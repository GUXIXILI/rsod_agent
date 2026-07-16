"""
对话 API 路由

提供 Agent/Chat 对话接口：
- POST   /api/chat/sessions                       — 创建会话
- GET    /api/chat/sessions                       — 会话列表（分页）
- GET    /api/chat/sessions/{session_id}/messages  — 消息历史
- POST   /api/chat/messages/stream                — 流式发送消息（SSE）
- POST   /api/chat/messages                       — 发送消息
- POST   /api/chat/upload                         — 上传文件
- DELETE /api/chat/sessions/{session_id}           — 删除会话
"""
import time
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import get_db
from app.entity.db_models import ChatSession
from app.entity.schemas import ChatSessionCreate, ChatMessageRequest
from app.services.chat_service import chat_service
from app.storage.minio_client import MinIOClient
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class RenameSessionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)


# 文件上传大小限制（字节）
MAX_IMAGE_SIZE = 10 * 1024 * 1024      # 10 MB
MAX_ZIP_SIZE = 50 * 1024 * 1024         # 50 MB
MAX_VIDEO_SIZE = 50 * 1024 * 1024        # 50 MB

# 文件类型到 MIME 类型的映射
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "bmp", "gif", "webp"}
ZIP_EXTENSIONS = {"zip"}
VIDEO_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "webm"}


@router.post("/upload")
async def upload_chat_file(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    """
    上传聊天文件到 MinIO

    - 支持图片（jpg/jpeg/png/bmp/gif/webp，最大 10MB）
    - 支持 ZIP 压缩包（最大 50MB）
    - 支持视频（mp4/avi/mov/mkv/webm，最大 50MB）
    - 返回文件 URL、类型和名称
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    # 确定文件类型和大小限制
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext in IMAGE_EXTENSIONS:
        file_type = "image"
        max_size = MAX_IMAGE_SIZE
    elif ext in ZIP_EXTENSIONS:
        file_type = "zip"
        max_size = MAX_ZIP_SIZE
    elif ext in VIDEO_EXTENSIONS:
        file_type = "video"
        max_size = MAX_VIDEO_SIZE
    else:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: .{ext}，支持的格式：图片（{'/'.join(sorted(IMAGE_EXTENSIONS))}）、ZIP、视频（{'/'.join(sorted(VIDEO_EXTENSIONS))}）",
        )

    # 读取文件内容并校验大小
    file_bytes = await file.read()
    if len(file_bytes) > max_size:
        size_mb = max_size // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"文件大小超过限制（{file_type} 最大 {size_mb}MB）",
        )

    # 上传到 MinIO
    timestamp = int(time.time())
    safe_filename = file.filename.replace(" ", "_")
    object_name = f"chat_uploads/{current_user.id}/{timestamp}_{safe_filename}"

    try:
        minio_client = MinIOClient()
        url = minio_client.upload_bytes(object_name, file_bytes, content_type=file.content_type or "application/octet-stream")
        logger.info(f"聊天文件上传成功: user_id={current_user.id}, file={file.filename}, type={file_type}")
    except Exception as e:
        logger.exception(f"聊天文件上传失败: user_id={current_user.id}, file={file.filename}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

    return {
        "code": 200,
        "message": "success",
        "data": {
            "url": url,
            "type": file_type,
            "name": file.filename,
        },
    }


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session(
    request: ChatSessionCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建新的对话会话"""
    session = chat_service.create_session(db, current_user.id, request.title)
    return {
        "code": 200,
        "message": "创建成功",
        "data": {
            "id": session.id,
            "session_uuid": session.session_uuid,
            "title": session.title,
            "status": session.status,
            "message_count": session.message_count,
            "created_at": session.created_at,
        },
    }


@router.get("/sessions")
def get_sessions(
    skip: int = Query(0, ge=0, description="跳过条数"),
    limit: int = Query(20, ge=1, le=100, description="每页条数"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取用户会话列表（分页）"""
    result = chat_service.get_sessions(db, current_user.id, skip=skip, limit=limit)
    return {"code": 200, "message": "success", "data": result}


@router.get("/sessions/{session_id}/messages")
def get_session_messages(
    session_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取会话消息历史"""
    messages = chat_service.get_session_messages(db, session_id, current_user.id)
    return {"code": 200, "message": "success", "data": messages}


@router.post("/messages/stream")
async def send_message_stream(
    request: ChatMessageRequest,
    current_user=Depends(get_current_user),
):
    """SSE 流式发送消息"""
    return StreamingResponse(
        chat_service.send_message_stream(current_user.id, request, request.session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/messages")
def send_message(
    request: ChatMessageRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    发送消息
    - 如果 session_id 为空，自动创建新会话
    - 返回用户消息和 AI 回复
    """
    session_id = request.session_id

    # 如果没有传 session_id，自动创建新会话
    if not session_id:
        session = chat_service.create_session(db, current_user.id)
        session_id = session.id

    result = chat_service.send_message(db, session_id, current_user.id, request.content)
    return {"code": 200, "message": "success", "data": result}


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除会话（含消息级联删除）"""
    chat_service.delete_session(db, session_id, current_user.id)
    return {"code": 200, "message": "删除成功"}


@router.patch("/sessions/{session_id}")
def rename_session(
    session_id: int,
    data: RenameSessionRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """重命名会话"""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    session.title = data.title
    db.commit()
    return {"code": 200, "message": "重命名成功"}


@router.post("/detect-shortcut")
async def detect_shortcut(
    image: UploadFile = File(...),
    scene_id: int = Form(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """检测快捷 API — 直接调用检测服务，不经过 AI Agent"""
    from app.services.detection_service import detection_service
    image_bytes = await image.read()
    task = detection_service.detect_single(
        db=db, user_id=current_user.id, scene_id=scene_id,
        image_file=image_bytes, filename=image.filename,
    )
    return {"code": 200, "message": "检测完成", "data": {
        "task_id": task.id, "fire_level": task.fire_level,
        "fire_object_count": task.fire_object_count,
        "smoke_object_count": task.smoke_object_count,
        "annotated_url": task.annotated_url,
    }}
