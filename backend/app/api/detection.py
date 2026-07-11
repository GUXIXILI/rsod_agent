"""
检测 API 路由

提供火灾烟雾检测接口：
- POST /api/detection/single — 单图检测
- POST /api/detection/batch — 批量检测
- POST /api/detection/video — 视频检测
- GET /api/detection/tasks/{task_id} — 检测任务详情
- GET /api/detection/alerts — 火灾预警列表
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import get_db
from app.services.detection_service import detection_service

router = APIRouter(prefix="/api/detection", tags=["detection"])


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
        task = detection_service.detect_single(
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
                "annotated_url": task.annotated_url,
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
        image_files = [await f.read() for f in files]
        filenames = [f.filename or f"image_{i}.jpg" for i, f in enumerate(files)]
        tasks = detection_service.detect_batch(
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
        task = detection_service.detect_video(
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


@router.get("/tasks/{task_id}")
def get_detection_task(
    task_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取检测任务详情"""
    from app.services.history_service import history_service
    detail = history_service.get_task_detail(db, task_id)
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
    alerts = alert_service.get_alerts(db, scene_id=scene_id, limit=limit)
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