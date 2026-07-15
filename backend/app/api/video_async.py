"""
视频异步检测 API 路由

提供视频异步检测接口：
- POST /api/detection/video/async — 提交视频异步检测任务（立即返回 task_id）
- GET /api/detection/video/status/{task_id} — 查询视频检测任务进度和结果
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import get_db
from app.services.video_task_service import video_task_service
from app.services.history_service import history_service

router = APIRouter(prefix="/api/detection", tags=["detection-video-async"])


@router.post("/video/async")
async def detect_video_async(
    file: UploadFile = File(..., description="视频文件"),
    scene_id: int = Form(..., description="场景 ID"),
    conf_threshold: float = Form(0.25, description="置信度阈值"),
    iou_threshold: float = Form(0.45, description="NMS 阈值"),
    image_size: int = Form(640, description="推理图像尺寸"),
    frame_skip: int = Form(5, description="跳帧间隔"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """视频异步检测：上传视频文件，立即返回任务ID，后台线程处理"""
    try:
        video_bytes = await file.read()
        task = video_task_service.submit_video_task(
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
            "message": "视频检测任务已提交",
            "data": {
                "task_id": task.id,
                "status": "processing",
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"视频异步检测提交失败: {str(e)}",
        )


@router.get("/video/status/{task_id}")
def get_video_task_status(
    task_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询视频检测任务进度和结果"""
    progress_info = video_task_service.get_task_progress(task_id, db)

    # 查询完整任务详情
    detail = history_service.get_task_detail(db, task_id, current_user.id)

    data = {
        "task_id": task_id,
        "progress": progress_info.get("progress", 0),
    }

    if detail:
        data["status"] = detail["task"].get("status", "unknown") if isinstance(detail.get("task"), dict) else "unknown"
        data["detail"] = detail
    else:
        data["status"] = progress_info.get("status", "processing")

    return {
        "code": 200,
        "message": "success",
        "data": data,
    }
