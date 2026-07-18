from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api import training as training_api
from app.api.auth import get_current_user
from app.entity.db_models import DetectionScene, ModelVersion
from app.services.model_evaluation_service import ModelEvaluationError
from main import app


def _create_model_version(db_session, tmp_path, user_id):
    model_path = tmp_path / "best.pt"
    model_path.write_bytes(b"model")

    scene = DetectionScene(
        name="api_evaluation_scene",
        display_name="接口评估测试",
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
    return version


def test_model_evaluation_endpoint_requires_authentication(
    client: TestClient,
):
    response = client.post(
        "/api/training/models/1/evaluate",
        json={},
    )

    assert response.status_code == 401


def test_model_evaluation_endpoint_runs_and_returns_metrics(
    client: TestClient,
    db_session,
    create_test_user,
    tmp_path,
    monkeypatch,
):
    version = _create_model_version(
        db_session, tmp_path, create_test_user.id
    )
    captured = {}

    def fake_evaluate_and_save_model(db, **kwargs):
        captured.update(kwargs)
        version.precision = 0.765
        version.recall = 0.683
        version.map50 = 0.760
        version.map50_95 = 0.444
        version.per_class_ap = {
            "fire": 0.374,
            "smoke": 0.514,
        }
        return version, {
            "metrics": {
                "precision": 0.765,
                "recall": 0.683,
                "map50": 0.760,
                "map50_95": 0.444,
                "per_class_ap": {
                    "fire": 0.374,
                    "smoke": 0.514,
                },
            },
            "artifacts": {
                "output_directory": "evaluation-output",
            },
        }

    monkeypatch.setattr(
        training_api,
        "evaluate_and_save_model",
        fake_evaluate_and_save_model,
        raising=False,
    )
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=create_test_user.id,
        is_superuser=False,
    )
    try:
        response = client.post(
            f"/api/training/models/{version.id}/evaluate",
            json={
                "split": "val",
                "imgsz": 640,
                "batch": 8,
                "device": "cpu",
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    body = response.json()
    assert body["model_version_id"] == version.id
    assert body["metrics"]["map50"] == 0.760
    assert body["metrics"]["per_class_ap"]["fire"] == 0.374
    assert captured["model_version_id"] == version.id
    assert captured["split"] == "val"
    assert captured["imgsz"] == 640
    assert captured["batch"] == 8
    assert captured["device"] == "cpu"


def test_model_evaluation_endpoint_returns_not_found(
    client: TestClient,
    create_test_user,
):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=create_test_user.id,
        is_superuser=False,
    )
    try:
        response = client.post(
            "/api/training/models/99999/evaluate",
            json={},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 404
    assert response.json()["message"] == "模型版本不存在"


def test_model_evaluation_endpoint_rejects_unowned_model(
    client: TestClient,
    db_session,
    create_test_user,
    tmp_path,
):
    version = _create_model_version(db_session, tmp_path, None)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=create_test_user.id,
        is_superuser=False,
    )
    try:
        response = client.post(
            f"/api/training/models/{version.id}/evaluate",
            json={},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 403
    assert response.json()["message"] == "无权评估此模型版本"


def test_model_evaluation_endpoint_returns_service_error(
    client: TestClient,
    db_session,
    create_test_user,
    tmp_path,
    monkeypatch,
):
    version = _create_model_version(
        db_session, tmp_path, create_test_user.id
    )

    def raise_evaluation_error(db, **kwargs):
        raise ModelEvaluationError("evaluation failed")

    monkeypatch.setattr(
        training_api,
        "evaluate_and_save_model",
        raise_evaluation_error,
    )
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=create_test_user.id,
        is_superuser=False,
    )
    try:
        response = client.post(
            f"/api/training/models/{version.id}/evaluate",
            json={},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 400
    assert response.json()["message"] == "evaluation failed"


def test_model_evaluation_endpoint_validates_image_size(
    client: TestClient,
    create_test_user,
):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=create_test_user.id,
        is_superuser=False,
    )
    try:
        response = client.post(
            "/api/training/models/1/evaluate",
            json={"imgsz": 641},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 422
