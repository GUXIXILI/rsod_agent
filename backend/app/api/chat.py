"""
对话 API 路由

提供 Agent/Chat 对话接口：
- POST   /api/chat/sessions                       — 创建会话
- GET    /api/chat/sessions                       — 会话列表（分页）
- GET    /api/chat/sessions/{session_id}/messages  — 消息历史
- POST   /api/chat/messages/stream                — 流式发送消息（SSE）
- POST   /api/chat/messages                       — 发送消息
- DELETE /api/chat/sessions/{session_id}           — 删除会话
"""
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.config.settings import settings
from app.database.session import get_db
from app.entity.schemas import ChatAttachmentResponse, ChatSessionCreate, ChatMessageRequest
from app.services.chat_attachment_service import chat_attachment_service
from app.services.chat_service import chat_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/attachments", status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Store an attachment and return only an opaque attachment ID."""
    max_bytes = max(
        settings.CHAT_ATTACHMENT_MAX_IMAGE_BYTES,
        settings.CHAT_ATTACHMENT_MAX_VIDEO_BYTES,
        settings.CHAT_ATTACHMENT_MAX_ZIP_BYTES,
    )
    content = await file.read(max_bytes + 1)
    attachment = chat_attachment_service.upload(
        db=db,
        user_id=current_user.id,
        filename=file.filename,
        content_type=file.content_type,
        data=content,
    )
    payload = ChatAttachmentResponse(
        attachment_id=attachment.attachment_uuid,
        file_name=attachment.file_name,
        content_type=attachment.content_type,
        file_size=attachment.file_size,
        created_at=attachment.created_at,
    )
    return {"code": 200, "message": "success", "data": payload.model_dump()}


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

    result = chat_service.send_message(
        db,
        session_id,
        current_user.id,
        request.content,
        attachment_ids=request.attachment_ids,
    )
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
