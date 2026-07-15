"""User-scoped storage and retrieval for chat attachments."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.entity.db_models import ChatAttachment
from app.storage.minio_client import MinIOClient


IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".webp"}
VIDEO_SUFFIXES = {".avi", ".mkv", ".mov", ".mp4"}
ZIP_SUFFIXES = {".zip"}


@dataclass(frozen=True)
class AttachmentContent:
    """Attachment bytes resolved after ownership has been checked."""

    attachment_id: str
    file_name: str
    content_type: str
    data: bytes


class ChatAttachmentService:
    """Keeps chat uploads user-scoped and independent from local file paths."""

    def _safe_filename(self, filename: str | None) -> str:
        safe_name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
        if not safe_name or safe_name in {".", ".."}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Attachment filename is required")
        return safe_name

    def _max_size_for(self, suffix: str) -> int:
        if suffix in IMAGE_SUFFIXES:
            return settings.CHAT_ATTACHMENT_MAX_IMAGE_BYTES
        if suffix in VIDEO_SUFFIXES:
            return settings.CHAT_ATTACHMENT_MAX_VIDEO_BYTES
        if suffix in ZIP_SUFFIXES:
            return settings.CHAT_ATTACHMENT_MAX_ZIP_BYTES
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only image, video, and ZIP attachments are supported",
        )

    def _validate_upload(self, filename: str | None, content_type: str | None, data: bytes) -> str:
        safe_name = self._safe_filename(filename)
        suffix = Path(safe_name).suffix.lower()
        max_size = self._max_size_for(suffix)
        if not data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Attachment is empty")
        if len(data) > max_size:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Attachment exceeds the allowed size")
        if content_type and content_type != "application/octet-stream":
            valid_type = (
                (suffix in IMAGE_SUFFIXES and content_type.startswith("image/"))
                or (suffix in VIDEO_SUFFIXES and content_type.startswith("video/"))
                or (suffix in ZIP_SUFFIXES and content_type in {"application/zip", "application/x-zip-compressed"})
            )
            if not valid_type:
                raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Attachment MIME type does not match its extension")
        return safe_name

    def upload(
        self,
        db: Session,
        user_id: int,
        filename: str | None,
        content_type: str | None,
        data: bytes,
        storage: Any | None = None,
    ) -> ChatAttachment:
        safe_name = self._validate_upload(filename, content_type, data)
        attachment_id = str(uuid.uuid4())
        object_name = f"chat-attachments/{user_id}/{attachment_id}/{safe_name}"
        storage = storage or MinIOClient()
        storage.upload_bytes(object_name, data, content_type or "application/octet-stream")
        attachment = ChatAttachment(
            attachment_uuid=attachment_id,
            user_id=user_id,
            object_name=object_name,
            file_name=safe_name,
            content_type=content_type or "application/octet-stream",
            file_size=len(data),
        )
        try:
            db.add(attachment)
            db.commit()
            db.refresh(attachment)
            return attachment
        except Exception:
            db.rollback()
            try:
                storage.delete_file(object_name)
            finally:
                raise

    def resolve(self, db: Session, user_id: int, attachment_id: str, storage: Any | None = None) -> AttachmentContent:
        attachment = (
            db.query(ChatAttachment)
            .filter(ChatAttachment.attachment_uuid == attachment_id, ChatAttachment.user_id == user_id)
            .first()
        )
        if not attachment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment was not found")
        storage = storage or MinIOClient()
        return AttachmentContent(
            attachment_id=attachment.attachment_uuid,
            file_name=attachment.file_name,
            content_type=attachment.content_type,
            data=storage.download_bytes(attachment.object_name),
        )

    def bind_to_message(
        self,
        db: Session,
        user_id: int,
        session_id: int,
        message_id: int,
        attachment_ids: list[str] | None,
    ) -> list[ChatAttachment]:
        normalized_ids = list(dict.fromkeys(attachment_ids or []))
        if len(normalized_ids) > settings.CHAT_ATTACHMENT_MAX_COUNT:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Too many attachments")
        if not normalized_ids:
            return []
        attachments = (
            db.query(ChatAttachment)
            .filter(ChatAttachment.user_id == user_id, ChatAttachment.attachment_uuid.in_(normalized_ids))
            .all()
        )
        if len(attachments) != len(normalized_ids):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more attachments were not found")
        for attachment in attachments:
            if attachment.session_id not in {None, session_id} or attachment.message_id not in {None, message_id}:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attachment is already bound to another message")
            attachment.session_id = session_id
            attachment.message_id = message_id
        db.flush()
        return attachments


chat_attachment_service = ChatAttachmentService()
