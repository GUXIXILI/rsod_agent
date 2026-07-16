"""API contract tests for the opaque chat attachment upload endpoint."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.api import chat as chat_api
from app.api.auth import get_current_user
from main import app


def test_upload_attachment_returns_only_safe_metadata(client, monkeypatch):
    created = SimpleNamespace(
        attachment_uuid="3e6fb578-493d-441a-94c8-519b2e188b3a",
        file_name="camera.png",
        content_type="image/png",
        file_size=10,
        created_at="2026-07-16T00:00:00",
    )
    upload = MagicMock(return_value=created)
    monkeypatch.setattr(chat_api.chat_attachment_service, "upload", upload)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=9)
    try:
        response = client.post(
            "/api/chat/attachments",
            files={"file": ("camera.png", b"image-data", "image/png")},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["attachment_id"] == created.attachment_uuid
    assert "object_name" not in data
    upload.assert_called_once()
