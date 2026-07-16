import json
from types import SimpleNamespace

import pytest

from app.services.model_evaluation_service import (
    ModelEvaluationError,
    build_evaluation_summary,
    evaluate_model,
)


def _metrics(names=None, maps=None):
    return SimpleNamespace(
        names=names or {0: "fire", 1: "smoke"},
        box=SimpleNamespace(
            mp=0.765,
            mr=0.683,
            map50=0.760,
            map=0.444,
            maps=maps or [0.374, 0.514],
        ),
    )


def test_build_evaluation_summary_extracts_overall_and_class_metrics():
    result = build_evaluation_summary(_metrics())

    assert result["precision"] == pytest.approx(0.765)
    assert result["recall"] == pytest.approx(0.683)
    assert result["map50"] == pytest.approx(0.760)
    assert result["map50_95"] == pytest.approx(0.444)
    assert result["per_class_ap"] == {
        "fire": pytest.approx(0.374),
        "smoke": pytest.approx(0.514),
    }


def test_build_evaluation_summary_rejects_wrong_class_mapping():
    metrics = _metrics(names={0: "smoke", 1: "fire"})

    with pytest.raises(ModelEvaluationError, match="class mapping"):
        build_evaluation_summary(metrics)


def test_build_evaluation_summary_rejects_missing_box_metrics():
    metrics = SimpleNamespace(names={0: "fire", 1: "smoke"})

    with pytest.raises(ModelEvaluationError, match="box metrics"):
        build_evaluation_summary(metrics)


def test_build_evaluation_summary_rejects_class_metric_count_mismatch():
    metrics = _metrics(maps=[0.374])

    with pytest.raises(ModelEvaluationError, match="class metric count"):
        build_evaluation_summary(metrics)

def test_evaluate_model_runs_validation_and_writes_report(
    tmp_path, monkeypatch
):
    model_path = tmp_path / "best.pt"
    model_path.write_bytes(b"fake-model")
    data_path = tmp_path / "data.yaml"
    data_path.write_text("names: {0: fire, 1: smoke}\n", encoding="utf-8")
    output_dir = tmp_path / "evaluation"

    metrics = _metrics()
    metrics.save_dir = output_dir
    validation_calls = []

    class FakeModel:
        def val(self, **kwargs):
            validation_calls.append(kwargs)
            output_dir.mkdir(parents=True)
            (output_dir / "confusion_matrix.png").write_bytes(b"matrix")
            (
                output_dir / "confusion_matrix_normalized.png"
            ).write_bytes(b"normalized")
            return metrics

    monkeypatch.setattr(
        "app.services.model_evaluation_service.YOLO",
        lambda model: FakeModel(),
    )

    result = evaluate_model(
        model_path=model_path,
        data_path=data_path,
        output_dir=output_dir,
        split="val",
        imgsz=640,
        batch=8,
        device="cpu",
    )

    assert result["metrics"]["map50"] == pytest.approx(0.760)
    assert len(result["model_sha256"]) == 64
    assert result["artifacts"]["confusion_matrix"].endswith(
        "confusion_matrix.png"
    )
    assert result["artifacts"]["confusion_matrix_normalized"].endswith(
        "confusion_matrix_normalized.png"
    )

    report = json.loads(
        (output_dir / "evaluation.json").read_text(encoding="utf-8")
    )
    assert report["metrics"]["per_class_ap"] == {
        "fire": pytest.approx(0.374),
        "smoke": pytest.approx(0.514),
    }

    assert validation_calls == [{
        "data": str(data_path.resolve()),
        "split": "val",
        "imgsz": 640,
        "batch": 8,
        "device": "cpu",
        "workers": 0,
        "plots": True,
        "project": str(output_dir.parent.resolve()),
        "name": output_dir.name,
        "exist_ok": True,
        "verbose": False,
    }]


@pytest.mark.parametrize("missing_name", ["model", "data"])
def test_evaluate_model_rejects_missing_input_file(
    tmp_path, missing_name
):
    model_path = tmp_path / "best.pt"
    data_path = tmp_path / "data.yaml"

    if missing_name != "model":
        model_path.write_bytes(b"fake-model")
    if missing_name != "data":
        data_path.write_text("names: {}\n", encoding="utf-8")

    with pytest.raises(ModelEvaluationError, match="does not exist"):
        evaluate_model(
            model_path=model_path,
            data_path=data_path,
            output_dir=tmp_path / "evaluation",
        )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"imgsz": 288}, "imgsz"),
        ({"imgsz": 1312}, "imgsz"),
        ({"batch": 0}, "batch"),
        ({"batch": 65}, "batch"),
        ({"device": "0,1"}, "device"),
        ({"device": "cpu0"}, "device"),
    ],
)
def test_evaluate_model_rejects_invalid_runtime_parameters(
    tmp_path, overrides, message
):
    arguments = {
        "model_path": tmp_path / "missing-model.pt",
        "data_path": tmp_path / "missing-data.yaml",
        "output_dir": tmp_path / "evaluation",
        "imgsz": 640,
        "batch": 16,
        "device": "cpu",
    }
    arguments.update(overrides)

    with pytest.raises(ModelEvaluationError, match=message):
        evaluate_model(**arguments)


def test_evaluate_model_rejects_nonempty_output_directory(tmp_path):
    model_path = tmp_path / "best.pt"
    model_path.write_bytes(b"fake-model")
    data_path = tmp_path / "data.yaml"
    data_path.write_text("names: {0: fire, 1: smoke}\n", encoding="utf-8")
    output_dir = tmp_path / "evaluation"
    output_dir.mkdir()
    (output_dir / "old-result.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ModelEvaluationError, match="not empty"):
        evaluate_model(
            model_path=model_path,
            data_path=data_path,
            output_dir=output_dir,
        )
