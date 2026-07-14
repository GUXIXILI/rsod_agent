import pytest

from app.entity.db_models import DetectionScene, ModelVersion
from app.services.model_evaluation_service import (
    ModelEvaluationError,
    save_evaluation_result,
)


def _create_model_version(db_session, tmp_path):
    model_path = tmp_path / "best.pt"
    model_path.write_bytes(b"model-content")

    scene = DetectionScene(
        name="evaluation_scene",
        display_name="模型评估测试",
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


def _report(model_path):
    return {
        "model": str(model_path),
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
    }


def test_save_evaluation_result_updates_model_version(
    db_session, tmp_path
):
    version, model_path = _create_model_version(
        db_session, tmp_path
    )

    updated = save_evaluation_result(
        db_session,
        model_version_id=version.id,
        report=_report(model_path),
    )

    assert updated.precision == pytest.approx(0.765)
    assert updated.recall == pytest.approx(0.683)
    assert updated.map50 == pytest.approx(0.760)
    assert updated.map50_95 == pytest.approx(0.444)
    assert updated.per_class_ap == {
        "fire": pytest.approx(0.374),
        "smoke": pytest.approx(0.514),
    }
    assert updated.file_size == len(b"model-content")


def test_save_evaluation_result_rejects_missing_model_version(
    db_session, tmp_path
):
    model_path = tmp_path / "best.pt"
    model_path.write_bytes(b"model")

    with pytest.raises(ModelEvaluationError, match="not found"):
        save_evaluation_result(
            db_session,
            model_version_id=99999,
            report=_report(model_path),
        )


def test_save_evaluation_result_rejects_model_path_mismatch(
    db_session, tmp_path
):
    version, _ = _create_model_version(db_session, tmp_path)
    other_model = tmp_path / "other.pt"
    other_model.write_bytes(b"other")

    with pytest.raises(ModelEvaluationError, match="does not match"):
        save_evaluation_result(
            db_session,
            model_version_id=version.id,
            report=_report(other_model),
        )