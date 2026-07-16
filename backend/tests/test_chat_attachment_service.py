"""Tests for user-scoped chat attachment persistence and ownership checks."""

from dataclasses import dataclass

import pytest
from fastapi import HTTPException

from app.entity.db_models import ChatAttachment, User
from app.services.chat_attachment_service import ChatAttachmentService
from app.services.chat_service import chat_service


@dataclass
class FakeStorage:
    objects: dict[str, bytes]

    def upload_bytes(self, object_name: str, data: bytes, content_type: str) -> None:
        self.objects[object_name] = data

    def download_bytes(self, object_name: str) -> bytes:
        return self.objects[object_name]

    def delete_file(self, object_name: str) -> None:
        self.objects.pop(object_name, None)


def _create_other_user(db_session) -> User:
    other = User(
        username="attachment-other",
        email="attachment-other@example.com",
        hashed_password="not-used-by-this-test",
        is_active=True,
    )
    db_session.add(other)
    db_session.commit()
    return other


def test_upload_stores_an_opaque_user_owned_attachment(db_session, create_test_user):
    storage = FakeStorage({})
    service = ChatAttachmentService()

    attachment = service.upload(
        db_session,
        create_test_user.id,
        "camera.png",
        "image/png",
        b"image-data",
        storage=storage,
    )

    assert attachment.attachment_uuid
    assert attachment.object_name.startswith(f"chat-attachments/{create_test_user.id}/")
    assert storage.objects[attachment.object_name] == b"image-data"
    assert db_session.query(ChatAttachment).count() == 1


def test_upload_rejects_a_mismatched_mime_type(db_session, create_test_user):
    with pytest.raises(HTTPException) as error:
        ChatAttachmentService().upload(
            db_session,
            create_test_user.id,
            "camera.png",
            "video/mp4",
            b"image-data",
            storage=FakeStorage({}),
        )

    assert error.value.status_code == 415


def test_resolve_rejects_another_users_attachment(db_session, create_test_user):
    storage = FakeStorage({})
    service = ChatAttachmentService()
    attachment = service.upload(
        db_session,
        create_test_user.id,
        "camera.png",
        "image/png",
        b"image-data",
        storage=storage,
    )

    with pytest.raises(HTTPException) as error:
        service.resolve(db_session, _create_other_user(db_session).id, attachment.attachment_uuid, storage=storage)

    assert error.value.status_code == 404


def test_message_binding_is_owned_and_returned_in_history(db_session, create_test_user):
    storage = FakeStorage({})
    service = ChatAttachmentService()
    attachment = service.upload(
        db_session,
        create_test_user.id,
        "camera.png",
        "image/png",
        b"image-data",
        storage=storage,
    )
    session = chat_service.create_session(db_session, create_test_user.id)

    chat_service.send_message(
        db_session,
        session.id,
        create_test_user.id,
        "请分析附件",
        attachment_ids=[attachment.attachment_uuid],
    )

    messages = chat_service.get_session_messages(db_session, session.id, create_test_user.id)
    assert messages[0]["attachments"][0]["attachment_id"] == attachment.attachment_uuid
