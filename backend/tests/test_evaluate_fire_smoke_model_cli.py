import json

from app.services.model_evaluation_service import ModelEvaluationError
from tools.evaluate_fire_smoke_model import build_parser, main


def test_build_parser_uses_safe_defaults():
    args = build_parser().parse_args([])

    assert args.split == "val"
    assert args.imgsz == 640
    assert args.batch == 16
    assert args.device == "cpu"


def test_main_forwards_arguments_and_prints_report(
    tmp_path, monkeypatch, capsys
):
    model_path = tmp_path / "best.pt"
    data_path = tmp_path / "data.yaml"
    output_dir = tmp_path / "evaluation"
    captured = {}

    def fake_evaluate_model(**kwargs):
        captured.update(kwargs)
        return {
            "metrics": {"map50": 0.76},
            "artifacts": {
                "output_directory": str(output_dir),
            },
        }

    monkeypatch.setattr(
        "tools.evaluate_fire_smoke_model.evaluate_model",
        fake_evaluate_model,
    )

    exit_code = main([
        "--model", str(model_path),
        "--data", str(data_path),
        "--output", str(output_dir),
        "--split", "test",
        "--imgsz", "960",
        "--batch", "8",
        "--device", "0",
    ])

    assert exit_code == 0
    assert captured == {
        "model_path": model_path,
        "data_path": data_path,
        "output_dir": output_dir,
        "split": "test",
        "imgsz": 960,
        "batch": 8,
        "device": "0",
    }

    printed = json.loads(capsys.readouterr().out)
    assert printed["metrics"]["map50"] == 0.76


def test_main_returns_one_for_evaluation_error(
    tmp_path, monkeypatch, capsys
):
    def raise_error(**kwargs):
        raise ModelEvaluationError("model failed")

    monkeypatch.setattr(
        "tools.evaluate_fire_smoke_model.evaluate_model",
        raise_error,
    )

    exit_code = main([
        "--model", str(tmp_path / "missing.pt"),
        "--data", str(tmp_path / "data.yaml"),
        "--output", str(tmp_path / "evaluation"),
    ])

    assert exit_code == 1
    assert "ERROR: model failed" in capsys.readouterr().err