import pytest

from app.entity.db_models import DetectionScene, ModelVersion
from app.services.model_artifact_service import (
    ModelArtifactError,
    export_model_version,
    get_model_artifact,
)


def _create_model_version(db_session, tmp_path):
    model_path = tmp_path / "best.pt"
    model_path.write_bytes(b"model")
    scene = DetectionScene(
        name="artifact_scene",
        display_name="模型制品测试",
        category="fire",
        class_names=["fire", "smoke"],
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


def test_export_model_version_calls_ultralytics(
    db_session, tmp_path, monkeypatch
):
    version, model_path = _create_model_version(db_session, tmp_path)
    calls = []

    class FakeModel:
        def export(self, **kwargs):
            calls.append(kwargs)
            output = model_path.with_suffix(".onnx")
            output.write_bytes(b"onnx")
            return str(output)

    monkeypatch.setattr(
        "app.services.model_artifact_service.YOLO",
        lambda path: FakeModel(),
    )

    result = export_model_version(
        db_session,
        model_version_id=version.id,
        export_format="onnx",
        imgsz=640,
        device="cpu",
    )

    assert result == model_path.with_suffix(".onnx")
    assert calls == [{
        "format": "onnx",
        "imgsz": 640,
        "batch": 1,
        "device": "cpu",
        "half": False,
        "simplify": False,
    }]


def test_export_model_version_rejects_unsupported_format(
    db_session, tmp_path
):
    version, _ = _create_model_version(db_session, tmp_path)

    with pytest.raises(ModelArtifactError, match="Unsupported"):
        export_model_version(db_session, version.id, "engine")


def test_get_model_artifact_returns_original_weight(
    db_session, tmp_path
):
    version, model_path = _create_model_version(db_session, tmp_path)

    assert get_model_artifact(db_session, version.id, "pt") == model_path


def test_get_model_artifact_rejects_missing_export(
    db_session, tmp_path
):
    version, _ = _create_model_version(db_session, tmp_path)

    with pytest.raises(ModelArtifactError, match="does not exist"):
        get_model_artifact(db_session, version.id, "onnx")
