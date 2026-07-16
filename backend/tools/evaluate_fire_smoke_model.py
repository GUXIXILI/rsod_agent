"""独立运行火灾烟雾YOLO模型评估。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.model_evaluation_service import (  # noqa: E402
    ModelEvaluationError,
    evaluate_model,
    validate_evaluation_parameters,
)


def build_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        description="Evaluate a fire and smoke YOLO model"
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=(
            BACKEND_ROOT
            / "runs"
            / "fire_smoke"
            / "yolo11n_e50_b16_s42"
            / "weights"
            / "best.pt"
        ),
        help="Trained YOLO model path",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=(
            BACKEND_ROOT
            / "datasets"
            / "fire_smoke"
            / "yolo_dataset"
            / "data.yaml"
        ),
        help="YOLO data.yaml path",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            BACKEND_ROOT
            / "runs"
            / "fire_smoke"
            / "model_evaluation"
        ),
        help="Evaluation output directory",
    )
    parser.add_argument(
        "--split",
        choices=("val", "test"),
        default="val",
    )
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default="cpu")
    return parser


def main(argv: list[str] | None = None) -> int:
    """解析参数并运行模型评估。"""
    args = build_parser().parse_args(argv)

    try:
        validate_evaluation_parameters(
            imgsz=args.imgsz,
            batch=args.batch,
            device=args.device,
        )
        report = evaluate_model(
            model_path=args.model,
            data_path=args.data,
            output_dir=args.output,
            split=args.split,
            imgsz=args.imgsz,
            batch=args.batch,
            device=args.device,
        )
    except ModelEvaluationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
