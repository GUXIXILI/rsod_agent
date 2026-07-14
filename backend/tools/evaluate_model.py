"""对训练好的 YOLO 火灾烟雾模型执行评估，输出 mAP、precision、recall 等指标。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml


class EvaluationConfigurationError(RuntimeError):
    """评估配置不完整或不安全时抛出。"""


def validate_dataset_yaml(data_yaml: Path) -> dict[str, Any]:
    """验证数据集配置文件并解析路径。"""
    data_yaml = data_yaml.resolve()
    if not data_yaml.is_file():
        raise EvaluationConfigurationError(f"Dataset YAML not found: {data_yaml}")

    try:
        data = yaml.safe_load(data_yaml.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise EvaluationConfigurationError(
            f"Dataset YAML cannot be parsed: {data_yaml}"
        ) from exc

    if not isinstance(data, dict):
        raise EvaluationConfigurationError("data.yaml root must be a mapping")

    # 验证类别配置
    expected_class_count = 2
    nc = data.get("nc")
    if nc != expected_class_count:
        raise EvaluationConfigurationError(
            f"Expected nc={expected_class_count} for fire/smoke detection, got {nc}"
        )

    names = data.get("names")
    if names is None:
        raise EvaluationConfigurationError("data.yaml must define 'names' field")

    dataset_root_value = data.get("path", ".")
    dataset_root = Path(dataset_root_value)
    if not dataset_root.is_absolute():
        dataset_root = data_yaml.parent / dataset_root
    dataset_root = dataset_root.resolve()

    # 验证测试集路径存在
    resolved_splits: dict[str, str] = {}
    for split in ("test", "val"):
        split_value = data.get(split)
        if split_value is None or not str(split_value).strip():
            continue
        split_path = Path(split_value)
        if not split_path.is_absolute():
            split_path = dataset_root / split_path
        split_path = split_path.resolve()
        if split_path.exists():
            resolved_splits[split] = str(split_path)

    # 至少需要有一个评估集路径（val 或 test）
    if not resolved_splits:
        raise EvaluationConfigurationError(
            "data.yaml must define at least one of 'val' or 'test' path for evaluation"
        )

    return {
        "data_yaml": str(data_yaml),
        "dataset_root": str(dataset_root),
        "class_names": names,
        "splits": resolved_splits,
    }


def validate_numeric_arguments(args: argparse.Namespace) -> None:
    """验证数值参数范围。"""
    if args.batch <= 0:
        raise EvaluationConfigurationError("batch must be greater than zero")
    if args.imgsz < 320 or args.imgsz % 32 != 0:
        raise EvaluationConfigurationError(
            "imgsz must be at least 320 and divisible by 32"
        )
    if args.iou < 0 or args.iou > 1:
        raise EvaluationConfigurationError("iou threshold must be in [0, 1]")
    if args.conf < 0 or args.conf > 1:
        raise EvaluationConfigurationError("conf threshold must be in [0, 1]")
    if args.workers < 0:
        raise EvaluationConfigurationError("workers cannot be negative")


def validate_cuda_device(device: str) -> dict[str, Any]:
    """验证 CUDA 设备可用性。"""
    if device.lower() == "cpu":
        return {"device": "cpu", "cuda_available": False, "gpus": []}

    import torch

    if not torch.cuda.is_available():
        raise EvaluationConfigurationError(
            "CUDA is unavailable. Use --device cpu explicitly for CPU evaluation."
        )

    try:
        device_ids = [int(value.strip()) for value in device.split(",")]
    except ValueError as exc:
        raise EvaluationConfigurationError(
            f"Invalid CUDA device selection: {device}"
        ) from exc

    device_count = torch.cuda.device_count()
    invalid_ids = [device_id for device_id in device_ids if device_id >= device_count]
    if invalid_ids or any(device_id < 0 for device_id in device_ids):
        raise EvaluationConfigurationError(
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


def build_evaluation_arguments(args: argparse.Namespace) -> dict[str, Any]:
    """构造 YOLO 评估参数字典。"""
    return {
        "data": str(args.data.resolve()),
        "imgsz": args.imgsz,
        "batch": args.batch,
        "device": args.device,
        "iou": args.iou,
        "conf": args.conf,
        "workers": args.workers,
        "verbose": True,
        "save_json": args.save_json,
        "save_txt": args.save_txt,
        "plots": args.plots,
    }


def preflight(args: argparse.Namespace) -> dict[str, Any]:
    """执行所有预检查，返回结构化配置。"""
    validate_numeric_arguments(args)
    dataset = validate_dataset_yaml(args.data)
    device = validate_cuda_device(args.device)

    model = args.model.resolve()
    if not model.is_file():
        raise EvaluationConfigurationError(f"Model weights not found: {model}")

    project = args.project.resolve()
    run_name = args.name or f"eval_{model.stem}"
    run_directory = project / run_name
    if run_directory.exists():
        print(f"WARNING: Run directory {run_directory} already exists, results will be overwritten.")

    return {
        "model": str(model),
        "dataset": dataset,
        "device": device,
        "run_name": run_name,
        "run_directory": str(run_directory),
        "evaluation_arguments": build_evaluation_arguments(args),
    }


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    backend_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Evaluate a trained YOLO fire/smoke detection model"
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
        required=True,
        help="Path to trained model weights (.pt file)",
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=backend_root / "runs" / "evaluation",
        help="Evaluation output directory",
    )
    parser.add_argument("--name", help="Run directory name; generated when omitted")
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="0")
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument(
        "--iou",
        type=float,
        default=0.65,
        help="IoU threshold for NMS during evaluation",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="Confidence threshold during evaluation",
    )
    parser.add_argument(
        "--no-plots",
        dest="plots",
        action="store_false",
        default=True,
        help="Disable confusion matrix and PR curve plots",
    )
    parser.add_argument(
        "--save-json",
        action="store_true",
        default=False,
        help="Save predictions to JSON file",
    )
    parser.add_argument(
        "--save-txt",
        action="store_true",
        default=False,
        help="Save predictions to TXT files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print configuration without running evaluation",
    )
    return parser


def run_evaluation(args: argparse.Namespace, resolved: dict[str, Any]) -> dict[str, Any]:
    """执行 YOLO 模型评估并返回结果。"""
    from ultralytics import YOLO

    model = YOLO(resolved["model"])
    results = model.val(**resolved["evaluation_arguments"])

    # 提取关键指标
    metrics = {
        "box": {
            "map": results.box.map,
            "map50": results.box.map50,
            "map75": results.box.map75,
            "precision": results.box.precision,
            "recall": results.box.recall,
            "f1": results.box.f1,
        }
    }

    # 按类别输出
    if results.box.maps is not None:
        metrics["box"]["map_per_class"] = results.box.maps.tolist()

    print("\n" + "=" * 60)
    print("评估结果")
    print("=" * 60)
    print(f"mAP@0.5:        {metrics['box']['map50']:.4f}")
    print(f"mAP@0.5:0.95:   {metrics['box']['map']:.4f}")
    print(f"Precision:      {metrics['box']['precision']:.4f}")
    print(f"Recall:         {metrics['box']['recall']:.4f}")
    print(f"F1:             {metrics['box']['f1']:.4f}")
    if metrics["box"]["map_per_class"]:
        print(f"mAP per class:  {metrics['box']['map_per_class']}")
    print("=" * 60)
    print(f"Results saved to: {resolved['run_directory']}")

    return metrics


def main() -> int:
    args = build_parser().parse_args()
    try:
        resolved = preflight(args)
    except EvaluationConfigurationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(resolved, indent=2, ensure_ascii=False))
    if args.dry_run:
        print("Dry run completed; evaluation was not started.")
        return 0

    run_evaluation(args, resolved)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
