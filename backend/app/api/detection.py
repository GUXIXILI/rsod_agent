"""Authenticated fire/smoke inference and persisted detection endpoints."""

from __future__ import annotations

import asyncio
import base64
import json
from datetime import datetime
from io import BytesIO
from typing import Annotated, Any, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
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
from app.services.video_task_service import video_task_service

logger = get_logger(__name__)


MAX_IMAGE_BYTES = 20 * 1024 * 1024
# 允许的图像文件扩展名白名单（防止非图像文件被传入检测接口）
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "bmp", "webp", "tiff"}
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
        # 校验文件类型：拒绝非图像文件上传
        ext = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件类型 '.{ext}'，请上传 jpg/jpeg/png/bmp/webp/tiff 格式的图片",
            )
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
                "inference_time": task.total_inference_time or 0,
                "class_counts": {
                    "fire": task.fire_object_count or 0,
                    "smoke": task.smoke_object_count or 0,
                },
            },
        }
    except HTTPException:
        raise  # 直接透传 HTTPException（如文件类型校验、场景不存在等），避免被通用异常捕获
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
            # 校验文件类型：拒绝非图像文件上传
            ext = (f.filename or "").rsplit(".", 1)[-1].lower() if "." in (f.filename or "") else ""
            if ext not in ALLOWED_IMAGE_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"不支持的文件类型 '.{ext}'，请上传 jpg/jpeg/png/bmp/webp/tiff 格式的图片",
                )
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
    except HTTPException:
        raise  # 直接透传 HTTPException
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
    except HTTPException:
        raise  # 直接透传 HTTPException
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

        # 校验 ZIP 内文件类型：拒绝包含非图像文件的 ZIP 包
        import zipfile
        from pathlib import Path
        with zipfile.ZipFile(BytesIO(zip_bytes), "r") as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                # 处理中文编码
                try:
                    inner_name = info.filename.encode("cp437").decode("gbk")
                except (UnicodeDecodeError, UnicodeEncodeError):
                    try:
                        inner_name = info.filename.encode("cp437").decode("utf-8")
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        inner_name = info.filename
                ext = Path(inner_name).suffix.lstrip(".").lower()
                if ext and ext not in ALLOWED_IMAGE_EXTENSIONS:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"ZIP 包内包含不支持的文件类型 '.{ext}'（{inner_name}），请确保所有文件均为 jpg/jpeg/png/bmp/webp/tiff 格式的图片",
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
    except HTTPException:
        raise  # 直接透传 HTTPException
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"ZIP 检测失败: {str(e)}")


@router.get("/tasks/list")
def get_detection_tasks_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    fire_level: Optional[str] = Query(None, description="火情等级筛选"),
    file_name: Optional[str] = Query(None, description="文件名搜索"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """分页查询检测任务列表

    注意：此端点为向后兼容保留，内部直接委托给 history_service.get_tasks()。
    建议前端统一使用 GET /api/history/tasks 端点。
    """
    result = history_service.get_tasks(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        fire_level=fire_level,
        file_name=file_name,
        start_time=start_time,
        end_time=end_time,
    )
    return {"code": 200, "message": "success", "data": result}


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
def get_video_progress(
    task_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询视频检测进度，Redis 不可用时回查任务表。"""
    progress_info = video_task_service.get_task_progress(task_id, db)
    return {"code": 200, "data": progress_info}


# ══════════════════════════════════════════════════════════════
# WebSocket 摄像头实时检测
# 说明：未鉴权版本已删除，统一使用 app/api/camera.py 中带 JWT 鉴权的版本
# （main.py 已注册 camera_router，路由 /api/detection/camera 由 camera.py 提供）
# ══════════════════════════════════════════════════════════════
