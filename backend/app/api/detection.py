"""
检测 API 路由

提供火焰/烟雾检测的核心接口：
- POST /api/detection/image          — 单张图片检测（原始推理接口）
- POST /api/detection/video/frame    — 视频帧检测（逐帧确认）
- DELETE /api/detection/video/{stream_id} — 重置视频流确认状态
- POST /api/detection/single         — 单图检测（持久化版本）
- POST /api/detection/batch          — 批量图片检测
- POST /api/detection/video          — 视频文件检测
- POST /api/detection/zip            — ZIP 压缩包批量检测
- GET  /api/detection/tasks/{task_id} — 检测任务详情
- GET  /api/detection/alerts         — 火灾预警列表
- GET  /api/detection/video/progress/{task_id} — 视频检测进度
"""

from __future__ import annotations

import asyncio
import base64
import json
from io import BytesIO
from typing import Annotated, Any, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from PIL import Image, ImageDraw, UnidentifiedImageError
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.config.settings import settings
from app.core.logger import get_logger
from app.database.session import get_db
from app.services.detection_service import detection_service
from app.services.fire_smoke_detection_service import (
    ConfirmationState,
    FireSmokeDetectionService,
    fire_smoke_detection_service,
    video_confirmation_registry,
)
from app.services.history_service import history_service

logger = get_logger(__name__)


MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_VIDEO_BYTES = 500 * 1024 * 1024
router = APIRouter(prefix="/api/detection", tags=["detection"])


class DetectionItemResponse(BaseModel):
    class_id: int
    class_name: str
    confidence: float
    bbox: list[float]


class DetectionResponse(BaseModel):
    mode: str
    image_width: int
    image_height: int
    inference_time_ms: float
    thresholds: dict[str, float]
    counts: dict[str, int]
    detections: list[DetectionItemResponse]
    confirmation: dict[str, dict[str, Any]] | None = None
    confirmed_classes: list[str] = Field(default_factory=list)
    new_alert_classes: list[str] = Field(default_factory=list)


async def _read_image(file: UploadFile) -> Image.Image:
    """
    读取并校验上传的图片文件。

    校验内容：文件类型必须是 image/*、文件非空、大小不超过 20MB、
    文件内容为有效图片格式。校验通过后转换为 RGB 格式的 PIL Image。

    Args:
        file: FastAPI UploadFile 对象

    Returns:
        PIL.Image.Image: RGB 格式的图片对象

    Raises:
        HTTPException: 文件类型不支持、文件为空、文件过大或格式无效时抛出
    """
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only image uploads are supported",
        )
    content = await file.read(MAX_IMAGE_BYTES + 1)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image is empty",
        )
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Uploaded image exceeds 20 MiB",
        )
    try:
        return Image.open(BytesIO(content)).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid image",
        ) from exc


def _run_detection(
    image: Image.Image,
    fire_threshold: float,
    smoke_threshold: float,
    iou_threshold: float,
    image_size: int,
):
    """
    调用火灾烟雾检测服务执行推理。

    封装 fire_smoke_detection_service.detect() 调用，
    将检测异常转换为 HTTP 503 错误响应。

    Args:
        image: PIL Image 对象（RGB 格式）
        fire_threshold: 火焰类别置信度阈值
        smoke_threshold: 烟雾类别置信度阈值
        iou_threshold: NMS 非极大值抑制 IoU 阈值
        image_size: 推理图像尺寸

    Returns:
        InferenceResult: 检测结果对象

    Raises:
        HTTPException: 模型权重缺失、参数无效或推理失败时抛出 503
    """
    try:
        return fire_smoke_detection_service.detect(
            image=image,
            thresholds={
                "fire": fire_threshold,
                "smoke": smoke_threshold,
            },
            iou_threshold=iou_threshold,
            image_size=image_size,
        )
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


def _build_response(
    result,
    mode: str,
    thresholds: dict[str, float],
    confirmation: dict[str, ConfirmationState] | None = None,
) -> dict[str, Any]:
    """
    将检测结果组装为 API 响应字典。

    功能：
    1. 提取检测结果的核心字段（detections, image_width 等）
    2. 统计 fire 和 smoke 的检测数量
    3. 如果有连续帧确认状态，序列化确认信息
    4. 汇总所有字段到统一的响应格式

    Args:
        result: InferenceResult 检测结果对象
        mode: 检测模式（"image" 或 "video_frame"）
        thresholds: 各类别的置信度阈值配置
        confirmation: 连续帧确认状态映射（视频帧检测时传入）

    Returns:
        dict: 包含 mode、检测结果、阈值、计数、确认状态的响应字典
    """
    payload = result.to_dict()
    counts = {"fire": 0, "smoke": 0}
    for item in result.detections:
        counts[item.class_name] += 1
    serialized_confirmation = None
    confirmed_classes: list[str] = []
    new_alert_classes: list[str] = []
    if confirmation is not None:
        serialized_confirmation = {
            name: {
                "consecutive_frames": state.consecutive_frames,
                "required_frames": state.required_frames,
                "confirmed": state.confirmed,
                "newly_confirmed": state.newly_confirmed,
            }
            for name, state in confirmation.items()
        }
        confirmed_classes = [
            name for name, state in confirmation.items() if state.confirmed
        ]
        new_alert_classes = [
            name
            for name, state in confirmation.items()
            if state.newly_confirmed
        ]
    return {
        "mode": mode,
        **payload,
        "thresholds": thresholds,
        "counts": counts,
        "confirmation": serialized_confirmation,
        "confirmed_classes": confirmed_classes,
        "new_alert_classes": new_alert_classes,
    }


@router.post("/image", response_model=DetectionResponse)
async def detect_image(
    file: Annotated[UploadFile, File(...)],
    fire_threshold: Annotated[
        float,
        Form(ge=0.0, le=1.0),
    ] = settings.FIRE_SMOKE_IMAGE_FIRE_THRESHOLD,
    smoke_threshold: Annotated[
        float,
        Form(ge=0.0, le=1.0),
    ] = settings.FIRE_SMOKE_IMAGE_SMOKE_THRESHOLD,
    iou_threshold: Annotated[float, Form(ge=0.0, le=1.0)] = 0.45,
    image_size: Annotated[int, Form(ge=320, le=1280)] = 640,
    current_user=Depends(get_current_user),
):
    image = await _read_image(file)
    result = _run_detection(
        image,
        fire_threshold,
        smoke_threshold,
        iou_threshold,
        image_size,
    )
    return _build_response(
        result,
        mode="image",
        thresholds={"fire": fire_threshold, "smoke": smoke_threshold},
    )


@router.post("/video/frame", response_model=DetectionResponse)
async def detect_video_frame(
    file: Annotated[UploadFile, File(...)],
    stream_id: Annotated[str, Form(min_length=1, max_length=100)],
    fire_threshold: Annotated[
        float,
        Form(ge=0.0, le=1.0),
    ] = settings.FIRE_SMOKE_VIDEO_FIRE_THRESHOLD,
    smoke_threshold: Annotated[
        float,
        Form(ge=0.0, le=1.0),
    ] = settings.FIRE_SMOKE_VIDEO_SMOKE_THRESHOLD,
    fire_confirm_frames: Annotated[
        int,
        Form(ge=1, le=30),
    ] = settings.FIRE_SMOKE_FIRE_CONFIRM_FRAMES,
    smoke_confirm_frames: Annotated[
        int,
        Form(ge=1, le=30),
    ] = settings.FIRE_SMOKE_SMOKE_CONFIRM_FRAMES,
    iou_threshold: Annotated[float, Form(ge=0.0, le=1.0)] = 0.45,
    image_size: Annotated[int, Form(ge=320, le=1280)] = 640,
    current_user=Depends(get_current_user),
):
    image = await _read_image(file)
    result = _run_detection(
        image,
        fire_threshold,
        smoke_threshold,
        iou_threshold,
        image_size,
    )
    registry_key = f"{current_user.id}:{stream_id}"
    confirmation = video_confirmation_registry.update(
        stream_id=registry_key,
        detections=result.detections,
        required_frames={
            "fire": fire_confirm_frames,
            "smoke": smoke_confirm_frames,
        },
    )
    return _build_response(
        result,
        mode="video_frame",
        thresholds={"fire": fire_threshold, "smoke": smoke_threshold},
        confirmation=confirmation,
    )


@router.delete("/video/{stream_id}")
def reset_video_stream(
    stream_id: str,
    current_user=Depends(get_current_user),
):
    registry_key = f"{current_user.id}:{stream_id}"
    return {
        "stream_id": stream_id,
        "reset": video_confirmation_registry.reset(registry_key),
    }


@router.post("/single")
async def detect_single(
    file: UploadFile = File(..., description="图片文件"),
    scene_id: int = Form(..., description="场景 ID"),
    conf_threshold: float = Form(0.25, description="置信度阈值"),
    iou_threshold: float = Form(0.45, description="NMS 阈值"),
    image_size: int = Form(640, description="推理图像尺寸"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """单图检测：上传一张图片，检测火焰和烟雾"""
    try:
        image_bytes = await file.read()
        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Uploaded image exceeds 20 MiB",
            )
        task = await asyncio.to_thread(
            detection_service.detect_single,
            db=db,
            user_id=current_user.id,
            scene_id=scene_id,
            image_file=image_bytes,
            filename=file.filename or "image.jpg",
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            image_size=image_size,
        )
        return {
            "code": 200,
            "message": "检测完成",
            "data": {
                "task_id": task.id,
                "fire_level": task.fire_level,
                "fire_object_count": task.fire_object_count,
                "smoke_object_count": task.smoke_object_count,
                "total_objects": task.fire_object_count + task.smoke_object_count,
                "annotated_url": task.annotated_url,
                "annotated_image_base64": getattr(task, "annotated_image_base64", None),
                "inference_time": task.total_inference_time or 0,
                "class_counts": {
                    "fire": task.fire_object_count or 0,
                    "smoke": task.smoke_object_count or 0,
                },
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"检测失败: {str(e)}")


@router.post("/batch")
async def detect_batch(
    files: List[UploadFile] = File(..., description="图片文件列表"),
    scene_id: int = Form(..., description="场景 ID"),
    conf_threshold: float = Form(0.25, description="置信度阈值"),
    iou_threshold: float = Form(0.45, description="NMS 阈值"),
    image_size: int = Form(640, description="推理图像尺寸"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """批量检测：上传多张图片"""
    if len(files) > 20:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="单次最多上传 20 张图片")

    try:
        image_files = []
        for f in files:
            data = await f.read()
            if len(data) > MAX_IMAGE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File '{f.filename}' exceeds 20 MiB",
                )
            image_files.append(data)
        filenames = [f.filename or f"image_{i}.jpg" for i, f in enumerate(files)]
        tasks = await asyncio.to_thread(
            detection_service.detect_batch,
            db=db,
            user_id=current_user.id,
            scene_id=scene_id,
            image_files=image_files,
            filenames=filenames,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            image_size=image_size,
        )
        return {
            "code": 200,
            "message": "批量检测完成",
            "data": {
                "total": len(tasks),
                "total_objects": sum((t.fire_object_count or 0) + (t.smoke_object_count or 0) for t in tasks),
                "tasks": [
                    {
                        "task_id": t.id,
                        "fire_level": t.fire_level,
                        "fire_object_count": t.fire_object_count,
                        "smoke_object_count": t.smoke_object_count,
                    }
                    for t in tasks
                ],
            },
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"批量检测失败: {str(e)}")


@router.post("/video")
async def detect_video(
    file: UploadFile = File(..., description="视频文件"),
    scene_id: int = Form(..., description="场景 ID"),
    conf_threshold: float = Form(0.25, description="置信度阈值"),
    iou_threshold: float = Form(0.45, description="NMS 阈值"),
    image_size: int = Form(640, description="推理图像尺寸"),
    frame_skip: int = Form(5, description="跳帧间隔"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """视频检测：上传视频文件，逐帧检测"""
    try:
        video_bytes = await file.read()
        if len(video_bytes) > MAX_VIDEO_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Uploaded video exceeds 500 MiB",
            )
        task = await asyncio.to_thread(
            detection_service.detect_video,
            db=db,
            user_id=current_user.id,
            scene_id=scene_id,
            video_bytes=video_bytes,
            filename=file.filename or "video.mp4",
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            image_size=image_size,
            frame_skip=frame_skip,
        )
        return {
            "code": 200,
            "message": "视频检测完成",
            "data": {
                "task_id": task.id,
                "fire_level": task.fire_level,
                "fire_object_count": task.fire_object_count,
                "smoke_object_count": task.smoke_object_count,
                "annotated_url": task.annotated_url,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"视频检测失败: {str(e)}")


@router.post("/zip")
async def detect_zip(
    file: UploadFile = File(..., description="ZIP 压缩包，内含多张图片"),
    scene_id: int = Form(..., description="场景 ID"),
    conf_threshold: float = Form(0.25, description="置信度阈值"),
    iou_threshold: float = Form(0.45, description="NMS 阈值"),
    image_size: int = Form(640, description="推理图像尺寸"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """ZIP 批量检测：上传 ZIP 压缩包，对其中每张图片执行火焰烟雾检测

    支持的图片格式：jpg, jpeg, png, bmp, webp
    """
    # 校验文件类型
    if file.content_type and "zip" not in file.content_type and not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 ZIP 格式的压缩包",
        )

    try:
        zip_bytes = await file.read()
        if not zip_bytes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="上传的 ZIP 文件为空")
        if len(zip_bytes) > settings.ZIP_MAX_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"ZIP 文件超过最大限制 ({settings.ZIP_MAX_SIZE_MB} MB)",
            )

        # 调用检测服务
        tasks = await asyncio.to_thread(
            detection_service.detect_zip,
            db=db,
            user_id=current_user.id,
            scene_id=scene_id,
            zip_bytes=zip_bytes,
            filename=file.filename or "upload.zip",
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            image_size=image_size,
        )
        return {
            "code": 200,
            "message": "ZIP 批量检测完成",
            "data": {
                "total": len(tasks),
                "tasks": [
                    {
                        "task_id": t.id,
                        "file_name": t.file_name,
                        "fire_level": t.fire_level,
                        "fire_object_count": t.fire_object_count,
                        "smoke_object_count": t.smoke_object_count,
                        "status": t.status,
                    }
                    for t in tasks
                ],
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"ZIP 检测失败: {str(e)}")


@router.get("/tasks/{task_id}")
def get_detection_task(
    task_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取检测任务详情

    注意：此端点为向后兼容保留，内部直接委托给 history_service.get_task_detail()。
    建议前端统一使用 GET /api/history/tasks/{task_id} 端点。
    """
    detail = history_service.get_task_detail(db, task_id, current_user.id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="检测任务不存在")
    return {"code": 200, "message": "success", "data": detail}


@router.get("/alerts")
def get_fire_alerts(
    scene_id: Optional[int] = None,
    limit: int = 50,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取火灾预警列表"""
    from app.services.alert_service import alert_service
    alerts = alert_service.get_alerts(
        db, user_id=current_user.id, scene_id=scene_id, limit=limit
    )
    return {
        "code": 200,
        "message": "success",
        "data": [
            {
                "id": a.id,
                "task_id": a.task_id,
                "scene_id": a.scene_id,
                "fire_level": a.fire_level,
                "content": a.content,
                "suggestion": a.suggestion,
                "handled_status": a.handled_status,
                "created_at": a.created_at,
            }
            for a in alerts
        ],
    }


@router.get("/video/progress/{task_id}")
def get_video_progress(task_id: int, current_user=Depends(get_current_user)):
    """查询视频检测进度"""
    import redis, json
    from app.config.settings import settings as app_settings
    r = redis.Redis(host=app_settings.REDIS_HOST, port=app_settings.REDIS_PORT, db=app_settings.REDIS_DB, decode_responses=True)
    try:
        data = r.get(f"video:progress:{task_id}")
        if data:
            return {"code": 200, "message": "success", "data": json.loads(data)}
        return {"code": 200, "message": "任务未找到或已完成", "data": {"progress": -1}}
    except Exception:
        return {"code": 200, "message": "Redis 不可用", "data": {"progress": -1}}


# ══════════════════════════════════════════════════════════════
# WebSocket 摄像头实时检测
# 说明：未鉴权版本已删除，统一使用 app/api/camera.py 中带 JWT 鉴权的版本
# （main.py 已注册 camera_router，路由 /api/detection/camera 由 camera.py 提供）
# ══════════════════════════════════════════════════════════════
