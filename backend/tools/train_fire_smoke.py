"""为火灾烟雾检测数据集执行可复现的 YOLO 训练。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml


EXPECTED_CLASS_NAMES = {0: "fire", 1: "smoke"}


class TrainingConfigurationError(RuntimeError):
    """正式训练任务配置不安全或不完整时抛出。"""


def _normalize_names(names: Any) -> dict[int, str]:
    if isinstance(names, list):
        return {index: str(name) for index, name in enumerate(names)}
    if isinstance(names, dict):
        try:
            return {int(index): str(name) for index, name in names.items()}
        except (TypeError, ValueError) as exc:
            raise TrainingConfigurationError(
                "data.yaml names keys must be integer class IDs"
            ) from exc
    raise TrainingConfigurationError("data.yaml names must be a list or mapping")


def validate_dataset_yaml(data_yaml: Path) -> dict[str, Any]:
    data_yaml = data_yaml.resolve()
    if not data_yaml.is_file():
        raise TrainingConfigurationError(f"Dataset YAML not found: {data_yaml}")

    try:
        data = yaml.safe_load(data_yaml.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise TrainingConfigurationError(
            f"Dataset YAML cannot be parsed: {data_yaml}"
        ) from exc

    if not isinstance(data, dict):
        raise TrainingConfigurationError("data.yaml root must be a mapping")

    names = _normalize_names(data.get("names"))
    if names != EXPECTED_CLASS_NAMES:
        raise TrainingConfigurationError(
            f"Expected class mapping {EXPECTED_CLASS_NAMES}, got {names}"
        )
    if data.get("nc") != len(EXPECTED_CLASS_NAMES):
        raise TrainingConfigurationError(
            f"Expected nc={len(EXPECTED_CLASS_NAMES)}, got {data.get('nc')}"
        )

    dataset_root_value = data.get("path", ".")
    dataset_root = Path(dataset_root_value)
    if not dataset_root.is_absolute():
        dataset_root = data_yaml.parent / dataset_root
    dataset_root = dataset_root.resolve()

    resolved_splits: dict[str, str] = {}
    for split in ("train", "val", "test"):
        split_value = data.get(split)
        if not isinstance(split_value, str) or not split_value.strip():
            raise TrainingConfigurationError(
                f"data.yaml must define a non-empty {split} path"
            )
        split_path = Path(split_value)
        if not split_path.is_absolute():
            split_path = dataset_root / split_path
        split_path = split_path.resolve()
        if not split_path.exists():
            raise TrainingConfigurationError(
                f"Dataset {split} path not found: {split_path}"
            )
        resolved_splits[split] = str(split_path)

    return {
        "data_yaml": str(data_yaml),
        "dataset_root": str(dataset_root),
        "class_names": names,
        "splits": resolved_splits,
    }


def validate_numeric_arguments(args: argparse.Namespace) -> None:
    if args.epochs <= 0:
        raise TrainingConfigurationError("epochs must be greater than zero")
    if args.batch <= 0:
        raise TrainingConfigurationError("batch must be greater than zero")
    if args.imgsz < 320 or args.imgsz % 32 != 0:
        raise TrainingConfigurationError(
            "imgsz must be at least 320 and divisible by 32"
        )
    if args.patience < 0:
        raise TrainingConfigurationError("patience cannot be negative")
    if not 0.0 < args.fraction <= 1.0:
        raise TrainingConfigurationError("fraction must be in the range (0, 1]")
    if args.workers < 0:
        raise TrainingConfigurationError("workers cannot be negative")
    if args.save_period < -1 or args.save_period == 0:
        raise TrainingConfigurationError("save-period must be -1 or greater than zero")


def validate_cuda_device(device: str) -> dict[str, Any]:
    if device.lower() == "cpu":
        return {"device": "cpu", "cuda_available": False, "gpus": []}

    import torch

    if not torch.cuda.is_available():
        raise TrainingConfigurationError(
            "CUDA is unavailable. Use --device cpu explicitly only for debugging."
        )

    try:
        device_ids = [int(value.strip()) for value in device.split(",")]
    except ValueError as exc:
        raise TrainingConfigurationError(
            f"Invalid CUDA device selection: {device}"
        ) from exc

    device_count = torch.cuda.device_count()
    invalid_ids = [device_id for device_id in device_ids if device_id >= device_count]
    if invalid_ids or any(device_id < 0 for device_id in device_ids):
        raise TrainingConfigurationError(
            f"CUDA device {device} is invalid; available device count is {device_count}"
        )

    return {
        "device": device,
        "cuda_available": True,
        "gpus": [
            {
                "id": device_id,
                "name": torch.cuda.get_device_name(device_id),
                "memory_gb": round(
                    torch.cuda.get_device_properties(device_id).total_memory
                    / 1024**3,
                    2,
                ),
            }
            for device_id in device_ids
        ],
    }


def resolve_run_name(args: argparse.Namespace) -> str:
    if args.name:
        return args.name
    model_name = args.model.stem.replace(".", "_")
    return f"{model_name}_e{args.epochs}_b{args.batch}_s{args.seed}"


def build_training_arguments(args: argparse.Namespace, run_name: str) -> dict[str, Any]:
    return {
        "data": str(args.data.resolve()),
        "epochs": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "device": args.device,
        "workers": args.workers,
        "project": str(args.project.resolve()),
        "name": run_name,
        "exist_ok": False,
        "pretrained": True,
        "optimizer": "auto",
        "patience": args.patience,
        "seed": args.seed,
        "deterministic": True,
        "cache": False,
        "save": True,
        "save_period": args.save_period,
        "plots": True,
        "amp": args.amp,
        "fraction": args.fraction,
        "val": args.val,
        "verbose": True,
    }


def preflight(args: argparse.Namespace) -> dict[str, Any]:
    validate_numeric_arguments(args)
    dataset = validate_dataset_yaml(args.data)
    device = validate_cuda_device(args.device)

    model = args.model.resolve()
    if not model.is_file():
        raise TrainingConfigurationError(f"Pretrained model not found: {model}")

    project = args.project.resolve()
    run_name = resolve_run_name(args)
    run_directory = project / run_name
    if args.resume is None and run_directory.exists():
        raise TrainingConfigurationError(
            f"Run directory already exists; choose another --name: {run_directory}"
        )

    resume = None
    if args.resume is not None:
        resume = args.resume.resolve()
        if not resume.is_file():
            raise TrainingConfigurationError(f"Resume checkpoint not found: {resume}")

    return {
        "model": str(model),
        "dataset": dataset,
        "device": device,
        "run_name": run_name,
        "run_directory": str(run_directory),
        "resume": str(resume) if resume else None,
        "training_arguments": build_training_arguments(args, run_name),
    }


def build_parser() -> argparse.ArgumentParser:
    backend_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Preflight and run reproducible YOLO11 fire/smoke training"
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=backend_root / "datasets" / "fire_smoke" / "yolo_dataset" / "data.yaml",
        help="YOLO data.yaml path",
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=backend_root / "models" / "yolo11n.pt",
        help="Pretrained YOLO model path",
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=backend_root / "runs" / "fire_smoke",
        help="Training output parent directory",
    )
    parser.add_argument("--name", help="Run directory name; generated when omitted")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="0")
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--save-period", type=int, default=5)
    parser.add_argument("--fraction", type=float, default=1.0)
    parser.add_argument(
        "--amp",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable automatic mixed precision",
    )
    parser.add_argument(
        "--val",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run validation after every epoch",
    )
    parser.add_argument(
        "--resume",
        type=Path,
        help="Resume from a last.pt checkpoint using its saved arguments",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print the resolved configuration without training",
    )
    return parser


def run_training(args: argparse.Namespace, resolved: dict[str, Any]) -> None:
    from ultralytics import YOLO

    if args.resume is not None:
        model = YOLO(resolved["resume"])
        model.train(resume=True, device=args.device)
        return

    model = YOLO(resolved["model"])
    results = model.train(**resolved["training_arguments"])
    save_dir = getattr(results, "save_dir", resolved["run_directory"])
    print(f"Training results saved to: {save_dir}")


def main() -> int:
    args = build_parser().parse_args()
    try:
        resolved = preflight(args)
    except TrainingConfigurationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(resolved, indent=2, ensure_ascii=False))
    if args.dry_run:
        print("Dry run completed; training was not started.")
        return 0

    run_training(args, resolved)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
