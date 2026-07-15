from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api import training as training_api
from app.api.auth import get_current_user
from app.entity.db_models import DetectionScene, ModelVersion
from main import app


def _create_model_version(db_session, tmp_path, user_id):
    model_path = tmp_path / "best.pt"
    model_path.write_bytes(b"model-weights")
    scene = DetectionScene(
        name="artifact_api_scene",
        display_name="模型制品接口测试",
        category="fire",
        class_names=["fire", "smoke"],
        created_by=user_id,
    )
    db_session.add(scene)
    db_session.commit()
    db_session.refresh(scene)
    version = ModelVersion(
        scene_id=scene.id,
        version="v1.0.0",
        model_name="fire-smoke-yolo11n",
        model_type="yolov11n",
        model_path=str(model_path),
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)
    return version, model_path


def _override_user(user_id):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=user_id,
        is_superuser=False,
    )


def test_model_export_endpoint_requires_authentication(client: TestClient):
    response = client.post("/api/training/models/1/export", json={})

    assert response.status_code == 401


def test_model_export_endpoint_returns_artifact(
    client: TestClient,
    db_session,
    create_test_user,
    tmp_path,
    monkeypatch,
):
    version, model_path = _create_model_version(
        db_session, tmp_path, create_test_user.id
    )
    exported_path = model_path.with_suffix(".onnx")
    exported_path.write_bytes(b"onnx-model")
    captured = {}

    def fake_export_model_version(db, **kwargs):
        captured.update(kwargs)
        return exported_path

    monkeypatch.setattr(
        training_api,
        "export_model_version",
        fake_export_model_version,
    )
    _override_user(create_test_user.id)
    try:
        response = client.post(
            f"/api/training/models/{version.id}/export",
            json={"format": "onnx", "imgsz": 640, "device": "cpu"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json() == {
        "model_version_id": version.id,
        "format": "onnx",
        "file_name": "best.onnx",
        "file_size": len(b"onnx-model"),
    }
    assert captured["model_version_id"] == version.id
    assert captured["export_format"] == "onnx"


def test_model_download_endpoint_returns_weight(
    client: TestClient,
    db_session,
    create_test_user,
    tmp_path,
):
    version, _ = _create_model_version(
        db_session, tmp_path, create_test_user.id
    )
    _override_user(create_test_user.id)
    try:
        response = client.get(
            f"/api/training/models/{version.id}/download?format=pt"
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.content == b"model-weights"
    assert "best.pt" in response.headers["content-disposition"]


def test_model_download_endpoint_returns_missing_export(
    client: TestClient,
    db_session,
    create_test_user,
    tmp_path,
):
    version, _ = _create_model_version(
        db_session, tmp_path, create_test_user.id
    )
    _override_user(create_test_user.id)
    try:
        response = client.get(
            f"/api/training/models/{version.id}/download?format=onnx"
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 404
