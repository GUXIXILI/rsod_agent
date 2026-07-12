"""Analyze fire/smoke detection errors and confidence-threshold tradeoffs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from tools.train_fire_smoke import (  # noqa: E402
    TrainingConfigurationError,
    validate_cuda_device,
    validate_dataset_yaml,
)


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


@dataclass(frozen=True)
class Prediction:
    class_id: int
    confidence: float
    box: tuple[float, float, float, float]


@dataclass(frozen=True)
class ImageRecord:
    image_path: Path
    ground_truths: tuple[tuple[int, tuple[float, float, float, float]], ...]
    predictions: tuple[Prediction, ...]


@dataclass(frozen=True)
class MatchResult:
    true_positives: int
    false_positives: int
    false_negatives: int
    unmatched_ground_truths: tuple[tuple[float, float, float, float], ...]
    unmatched_predictions: tuple[Prediction, ...]


class ErrorAnalysisError(RuntimeError):
    """Raised when error analysis cannot be completed safely."""


def parse_thresholds(value: str) -> tuple[float, ...]:
    try:
        thresholds = sorted({float(item.strip()) for item in value.split(",")})
    except ValueError as exc:
        raise argparse.ArgumentTypeError("thresholds must be comma-separated numbers") from exc
    if not thresholds or any(not 0.0 < threshold < 1.0 for threshold in thresholds):
        raise argparse.ArgumentTypeError("each threshold must be in the range (0, 1)")
    return tuple(thresholds)


def box_iou(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> float:
    intersection_x1 = max(first[0], second[0])
    intersection_y1 = max(first[1], second[1])
    intersection_x2 = min(first[2], second[2])
    intersection_y2 = min(first[3], second[3])
    intersection_width = max(0.0, intersection_x2 - intersection_x1)
    intersection_height = max(0.0, intersection_y2 - intersection_y1)
    intersection = intersection_width * intersection_height

    first_area = max(0.0, first[2] - first[0]) * max(0.0, first[3] - first[1])
    second_area = max(0.0, second[2] - second[0]) * max(0.0, second[3] - second[1])
    union = first_area + second_area - intersection
    return intersection / union if union > 0.0 else 0.0


def match_class(
    ground_truths: Iterable[tuple[float, float, float, float]],
    predictions: Iterable[Prediction],
    confidence_threshold: float,
    iou_threshold: float,
) -> MatchResult:
    ground_truth_list = list(ground_truths)
    prediction_list = sorted(
        (
            prediction
            for prediction in predictions
            if prediction.confidence >= confidence_threshold
        ),
        key=lambda prediction: prediction.confidence,
        reverse=True,
    )
    unmatched_ground_truth_indices = set(range(len(ground_truth_list)))
    unmatched_predictions: list[Prediction] = []
    true_positives = 0

    for prediction in prediction_list:
        best_index = None
        best_iou = 0.0
        for ground_truth_index in unmatched_ground_truth_indices:
            current_iou = box_iou(
                prediction.box, ground_truth_list[ground_truth_index]
            )
            if current_iou > best_iou:
                best_iou = current_iou
                best_index = ground_truth_index
        if best_index is not None and best_iou >= iou_threshold:
            unmatched_ground_truth_indices.remove(best_index)
            true_positives += 1
        else:
            unmatched_predictions.append(prediction)

    unmatched_ground_truths = tuple(
        ground_truth_list[index] for index in sorted(unmatched_ground_truth_indices)
    )
    return MatchResult(
        true_positives=true_positives,
        false_positives=len(unmatched_predictions),
        false_negatives=len(unmatched_ground_truths),
        unmatched_ground_truths=unmatched_ground_truths,
        unmatched_predictions=tuple(unmatched_predictions),
    )


def _safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def evaluate_records(
    records: Iterable[ImageRecord],
    thresholds: Iterable[float],
    class_names: dict[int, str],
    iou_threshold: float,
) -> list[dict[str, Any]]:
    record_list = list(records)
    rows: list[dict[str, Any]] = []
    for threshold in thresholds:
        for class_id, class_name in sorted(class_names.items()):
            true_positives = 0
            false_positives = 0
            false_negatives = 0
            negative_images = 0
            negative_alarm_images = 0
            negative_false_positives = 0
            for record in record_list:
                ground_truths = [
                    box
                    for ground_truth_class, box in record.ground_truths
                    if ground_truth_class == class_id
                ]
                predictions = [
                    prediction
                    for prediction in record.predictions
                    if prediction.class_id == class_id
                ]
                match = match_class(
                    ground_truths,
                    predictions,
                    confidence_threshold=threshold,
                    iou_threshold=iou_threshold,
                )
                true_positives += match.true_positives
                false_positives += match.false_positives
                false_negatives += match.false_negatives
                if not ground_truths:
                    negative_images += 1
                    negative_false_positives += match.false_positives
                    if match.false_positives:
                        negative_alarm_images += 1

            precision = _safe_ratio(
                true_positives, true_positives + false_positives
            )
            recall = _safe_ratio(true_positives, true_positives + false_negatives)
            f1 = (
                2.0 * precision * recall / (precision + recall)
                if precision + recall > 0.0
                else 0.0
            )
            rows.append(
                {
                    "threshold": threshold,
                    "class_id": class_id,
                    "class_name": class_name,
                    "tp": true_positives,
                    "fp": false_positives,
                    "fn": false_negatives,
                    "negative_images": negative_images,
                    "negative_alarm_images": negative_alarm_images,
                    "negative_alarm_rate": _safe_ratio(
                        negative_alarm_images, negative_images
                    ),
                    "negative_predictions_per_image": _safe_ratio(
                        negative_false_positives, negative_images
                    ),
                    "precision": precision,
                    "recall": recall,
                    "f1": f1,
                }
            )
    return rows


def recommend_threshold(
    rows: Iterable[dict[str, Any]], class_id: int, minimum_precision: float
) -> dict[str, Any] | None:
    candidates = [
        row
        for row in rows
        if row["class_id"] == class_id and row["precision"] >= minimum_precision
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda row: (row["recall"], row["f1"], row["precision"], row["threshold"]),
    )


def _read_ground_truths(
    label_path: Path, image_width: int, image_height: int
) -> tuple[tuple[int, tuple[float, float, float, float]], ...]:
    if not label_path.is_file():
        raise ErrorAnalysisError(f"Label file not found: {label_path}")

    ground_truths: list[tuple[int, tuple[float, float, float, float]]] = []
    for line_number, raw_line in enumerate(
        label_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        stripped = raw_line.strip()
        if not stripped:
            continue
        parts = stripped.split()
        if len(parts) != 5:
            raise ErrorAnalysisError(
                f"{label_path}:{line_number} must contain exactly 5 values"
            )
        try:
            class_id = int(parts[0])
            x_center, y_center, width, height = [
                float(value) for value in parts[1:]
            ]
        except ValueError as exc:
            raise ErrorAnalysisError(
                f"{label_path}:{line_number} contains invalid numeric data"
            ) from exc
        box = (
            max(0.0, (x_center - width / 2.0) * image_width),
            max(0.0, (y_center - height / 2.0) * image_height),
            min(float(image_width), (x_center + width / 2.0) * image_width),
            min(float(image_height), (y_center + height / 2.0) * image_height),
        )
        ground_truths.append((class_id, box))
    return tuple(ground_truths)


def collect_predictions(
    model_path: Path,
    image_directory: Path,
    label_directory: Path,
    minimum_confidence: float,
    image_size: int,
    batch_size: int,
    device: str,
    maximum_images: int,
) -> list[ImageRecord]:
    from ultralytics import YOLO

    image_paths = sorted(
        path
        for path in image_directory.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )
    if maximum_images > 0:
        image_paths = image_paths[:maximum_images]
    if not image_paths:
        raise ErrorAnalysisError(f"No images found in: {image_directory}")

    model = YOLO(str(model_path))
    records: list[ImageRecord] = []
    for chunk_start in range(0, len(image_paths), batch_size):
        chunk_paths = image_paths[chunk_start : chunk_start + batch_size]
        prediction_results = model.predict(
            source=[str(path) for path in chunk_paths],
            stream=False,
            conf=minimum_confidence,
            iou=0.7,
            imgsz=image_size,
            batch=batch_size,
            device=device,
            save=False,
            verbose=False,
        )
        for result in prediction_results:
            image_path = Path(result.path).resolve()
            image_height, image_width = result.orig_shape
            label_path = label_directory / f"{image_path.stem}.txt"
            ground_truths = _read_ground_truths(
                label_path, image_width=image_width, image_height=image_height
            )

            predictions: list[Prediction] = []
            if result.boxes is not None and len(result.boxes) > 0:
                boxes = result.boxes.xyxy.cpu().numpy()
                confidences = result.boxes.conf.cpu().numpy()
                classes = result.boxes.cls.cpu().numpy().astype(int)
                for box, confidence, class_id in zip(boxes, confidences, classes):
                    predictions.append(
                        Prediction(
                            class_id=int(class_id),
                            confidence=float(confidence),
                            box=tuple(float(value) for value in box),
                        )
                    )
            records.append(
                ImageRecord(
                    image_path=image_path,
                    ground_truths=ground_truths,
                    predictions=tuple(predictions),
                )
            )
        processed_count = min(chunk_start + len(chunk_paths), len(image_paths))
        if processed_count % 500 < batch_size or processed_count == len(image_paths):
            print(f"Predicted {processed_count}/{len(image_paths)} images", flush=True)
    return records


def _draw_box(
    image: np.ndarray,
    box: tuple[float, float, float, float],
    color: tuple[int, int, int],
    label: str,
) -> None:
    import cv2

    x1, y1, x2, y2 = [int(round(value)) for value in box]
    cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
    text_y = max(18, y1 - 6)
    cv2.putText(
        image,
        label,
        (x1, text_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        color,
        2,
        cv2.LINE_AA,
    )


def _letterbox_tile(image: np.ndarray, title: str, width: int, height: int) -> np.ndarray:
    import cv2

    title_height = 34
    content_height = height - title_height
    scale = min(width / image.shape[1], content_height / image.shape[0])
    resized_width = max(1, int(round(image.shape[1] * scale)))
    resized_height = max(1, int(round(image.shape[0] * scale)))
    resized = cv2.resize(image, (resized_width, resized_height))
    tile = np.full((height, width, 3), 24, dtype=np.uint8)
    x_offset = (width - resized_width) // 2
    y_offset = title_height + (content_height - resized_height) // 2
    tile[y_offset : y_offset + resized_height, x_offset : x_offset + resized_width] = resized
    cv2.putText(
        tile,
        title[:60],
        (8, 23),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    return tile


def create_error_galleries(
    records: Iterable[ImageRecord],
    output_directory: Path,
    class_id: int,
    class_name: str,
    confidence_threshold: float,
    iou_threshold: float,
    maximum_items: int,
) -> dict[str, Any]:
    import cv2

    missed_entries: list[tuple[ImageRecord, MatchResult]] = []
    false_positive_entries: list[tuple[ImageRecord, MatchResult]] = []
    for record in records:
        ground_truths = [
            box
            for ground_truth_class, box in record.ground_truths
            if ground_truth_class == class_id
        ]
        predictions = [
            prediction
            for prediction in record.predictions
            if prediction.class_id == class_id
        ]
        match = match_class(
            ground_truths,
            predictions,
            confidence_threshold=confidence_threshold,
            iou_threshold=iou_threshold,
        )
        if match.false_negatives:
            missed_entries.append((record, match))
        if match.false_positives:
            false_positive_entries.append((record, match))

    missed_entries.sort(
        key=lambda item: (-item[1].false_negatives, item[0].image_path.name)
    )
    false_positive_entries.sort(
        key=lambda item: (
            -max(
                prediction.confidence
                for prediction in item[1].unmatched_predictions
            ),
            item[0].image_path.name,
        )
    )

    def write_gallery(
        entries: list[tuple[ImageRecord, MatchResult]],
        error_type: str,
        output_name: str,
    ) -> str | None:
        selected = entries[:maximum_items]
        if not selected:
            return None
        tiles: list[np.ndarray] = []
        for record, match in selected:
            image = cv2.imread(str(record.image_path))
            if image is None:
                continue
            for ground_truth_class, box in record.ground_truths:
                if ground_truth_class == class_id:
                    _draw_box(image, box, (0, 180, 0), f"GT {class_name}")
            for missed_box in match.unmatched_ground_truths:
                _draw_box(image, missed_box, (0, 0, 255), f"MISSED {class_name}")
            for prediction in match.unmatched_predictions:
                _draw_box(
                    image,
                    prediction.box,
                    (0, 220, 255),
                    f"FP {class_name} {prediction.confidence:.2f}",
                )
            title = (
                f"{record.image_path.name} | {error_type} "
                f"FN={match.false_negatives} FP={match.false_positives}"
            )
            tiles.append(_letterbox_tile(image, title, width=480, height=340))
        if not tiles:
            return None
        columns = 4
        rows = math.ceil(len(tiles) / columns)
        blank = np.full_like(tiles[0], 24)
        while len(tiles) < rows * columns:
            tiles.append(blank.copy())
        gallery_rows = [
            np.hstack(tiles[row * columns : (row + 1) * columns])
            for row in range(rows)
        ]
        output_path = output_directory / output_name
        cv2.imwrite(str(output_path), np.vstack(gallery_rows))
        return output_name

    return {
        "threshold": confidence_threshold,
        "missed_image_count": len(missed_entries),
        "false_positive_image_count": len(false_positive_entries),
        "missed_gallery": write_gallery(
            missed_entries, "false negatives", f"{class_name}_misses.jpg"
        ),
        "false_positive_gallery": write_gallery(
            false_positive_entries,
            "false positives",
            f"{class_name}_false_positives.jpg",
        ),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "threshold",
        "class_id",
        "class_name",
        "tp",
        "fp",
        "fn",
        "negative_images",
        "negative_alarm_images",
        "negative_alarm_rate",
        "negative_predictions_per_image",
        "precision",
        "recall",
        "f1",
    ]
    with path.open("w", encoding="utf-8", newline="") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sweep thresholds and visualize fire/smoke detection errors"
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=BACKEND_ROOT
        / "runs"
        / "fire_smoke"
        / "yolo11n_e50_b16_s42"
        / "weights"
        / "best.pt",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=BACKEND_ROOT
        / "datasets"
        / "fire_smoke"
        / "yolo_dataset"
        / "data.yaml",
    )
    parser.add_argument("--split", choices=("val", "test"), default="test")
    parser.add_argument(
        "--thresholds",
        type=parse_thresholds,
        default=parse_thresholds("0.05,0.10,0.15,0.20,0.25,0.30,0.35"),
    )
    parser.add_argument("--iou-threshold", type=float, default=0.5)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default="0")
    parser.add_argument("--minimum-fire-precision", type=float, default=0.65)
    parser.add_argument("--minimum-smoke-precision", type=float, default=0.70)
    parser.add_argument("--max-gallery-items", type=int, default=16)
    parser.add_argument(
        "--max-images",
        type=int,
        default=0,
        help="Limit images for debugging; zero analyzes the complete split",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=BACKEND_ROOT / "runs" / "fire_smoke" / "error_analysis_e50",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def validate_arguments(args: argparse.Namespace) -> dict[str, Any]:
    if not 0.0 < args.iou_threshold <= 1.0:
        raise ErrorAnalysisError("iou-threshold must be in the range (0, 1]")
    if args.imgsz < 320 or args.imgsz % 32 != 0:
        raise ErrorAnalysisError("imgsz must be at least 320 and divisible by 32")
    if args.batch <= 0:
        raise ErrorAnalysisError("batch must be greater than zero")
    if args.max_gallery_items <= 0:
        raise ErrorAnalysisError("max-gallery-items must be greater than zero")
    if args.max_images < 0:
        raise ErrorAnalysisError("max-images cannot be negative")
    for value, name in (
        (args.minimum_fire_precision, "minimum-fire-precision"),
        (args.minimum_smoke_precision, "minimum-smoke-precision"),
    ):
        if not 0.0 <= value <= 1.0:
            raise ErrorAnalysisError(f"{name} must be in the range [0, 1]")

    model_path = args.model.resolve()
    if not model_path.is_file():
        raise ErrorAnalysisError(f"Model not found: {model_path}")
    try:
        dataset = validate_dataset_yaml(args.data)
        device = validate_cuda_device(args.device)
    except TrainingConfigurationError as exc:
        raise ErrorAnalysisError(str(exc)) from exc

    image_directory = Path(dataset["splits"][args.split])
    label_directory = Path(dataset["dataset_root"]) / "labels" / args.split
    if not label_directory.is_dir():
        raise ErrorAnalysisError(f"Label directory not found: {label_directory}")
    image_count = sum(
        1
        for path in image_directory.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )
    if args.max_images > 0:
        image_count = min(image_count, args.max_images)

    output_directory = args.output.resolve()
    if output_directory.exists():
        raise ErrorAnalysisError(
            f"Output directory already exists; choose another --output: {output_directory}"
        )
    return {
        "model": model_path,
        "dataset": dataset,
        "device": device,
        "image_directory": image_directory,
        "label_directory": label_directory,
        "image_count": image_count,
        "output_directory": output_directory,
    }


def main() -> int:
    args = build_parser().parse_args()
    try:
        resolved = validate_arguments(args)
    except ErrorAnalysisError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    printable = {
        "model": str(resolved["model"]),
        "split": args.split,
        "image_count": resolved["image_count"],
        "thresholds": args.thresholds,
        "iou_threshold": args.iou_threshold,
        "device": resolved["device"],
        "output": str(resolved["output_directory"]),
    }
    print(json.dumps(printable, indent=2, ensure_ascii=False))
    if args.dry_run:
        print("Dry run completed; inference was not started.")
        return 0

    output_directory: Path = resolved["output_directory"]
    staging_directory = output_directory.with_name(f"{output_directory.name}.staging")
    if staging_directory.exists():
        raise ErrorAnalysisError(
            f"Staging directory already exists; inspect it first: {staging_directory}"
        )
    staging_directory.mkdir(parents=True)

    try:
        records = collect_predictions(
            model_path=resolved["model"],
            image_directory=resolved["image_directory"],
            label_directory=resolved["label_directory"],
            minimum_confidence=min(args.thresholds),
            image_size=args.imgsz,
            batch_size=args.batch,
            device=args.device,
            maximum_images=args.max_images,
        )
        class_names = {0: "fire", 1: "smoke"}
        rows = evaluate_records(
            records,
            thresholds=args.thresholds,
            class_names=class_names,
            iou_threshold=args.iou_threshold,
        )
        fire_recommendation = recommend_threshold(
            rows, class_id=0, minimum_precision=args.minimum_fire_precision
        )
        smoke_recommendation = recommend_threshold(
            rows, class_id=1, minimum_precision=args.minimum_smoke_precision
        )
        fire_gallery_threshold = (
            fire_recommendation["threshold"]
            if fire_recommendation is not None
            else min(args.thresholds)
        )
        galleries = create_error_galleries(
            records,
            output_directory=staging_directory,
            class_id=0,
            class_name="fire",
            confidence_threshold=fire_gallery_threshold,
            iou_threshold=args.iou_threshold,
            maximum_items=args.max_gallery_items,
        )

        _write_csv(staging_directory / "threshold_metrics.csv", rows)
        report = {
            "model": str(resolved["model"]),
            "model_sha256": _sha256(resolved["model"]),
            "split": args.split,
            "image_count": len(records),
            "iou_threshold": args.iou_threshold,
            "thresholds": list(args.thresholds),
            "minimum_precision": {
                "fire": args.minimum_fire_precision,
                "smoke": args.minimum_smoke_precision,
            },
            "recommendations": {
                "fire": fire_recommendation,
                "smoke": smoke_recommendation,
            },
            "metrics": rows,
            "galleries": galleries,
        }
        (staging_directory / "analysis_report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        staging_directory.rename(output_directory)
    except Exception:
        if staging_directory.exists():
            shutil.rmtree(staging_directory)
        raise

    print(json.dumps(report["recommendations"], indent=2, ensure_ascii=False))
    print(f"Analysis results saved to: {output_directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
