"""为团队火灾烟雾项目准备 D-Fire YOLO 数据集。

源数据集使用 0=smoke、1=fire，项目约定使用 0=fire、1=smoke。
因此脚本会重映射所有非空标签，同时保持源目录内容不变。
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from collections import Counter
from pathlib import Path


SPLITS = ("train", "val", "test")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
SOURCE_TO_TARGET_CLASS = {0: 1, 1: 0}
TARGET_CLASS_NAMES = {0: "fire", 1: "smoke"}
DATASET_SOURCE_URL = (
    "https://www.kaggle.com/datasets/sayedgamal99/smoke-fire-detection-yolo"
)


class DatasetPreparationError(RuntimeError):
    """源数据集无法安全转换时抛出。"""


def _files_by_stem(directory: Path, extensions: set[str]) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path in sorted(directory.iterdir()):
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        if path.stem in files:
            raise DatasetPreparationError(
                f"Duplicate file stem in {directory}: {path.stem}"
            )
        files[path.stem] = path
    return files


def _transform_label(
    label_path: Path,
) -> tuple[list[str], Counter, Counter, Counter]:
    transformed_lines: list[str] = []
    source_counts: Counter = Counter()
    target_counts: Counter = Counter()
    cleaning_counts: Counter = Counter()

    for line_number, raw_line in enumerate(
        label_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        stripped = raw_line.strip()
        if not stripped:
            continue

        parts = stripped.split()
        if len(parts) != 5:
            raise DatasetPreparationError(
                f"{label_path}:{line_number} must contain exactly 5 values"
            )

        try:
            source_class = int(parts[0])
            coordinates = [float(value) for value in parts[1:]]
        except ValueError as exc:
            raise DatasetPreparationError(
                f"{label_path}:{line_number} contains a non-numeric value"
            ) from exc

        if source_class not in SOURCE_TO_TARGET_CLASS:
            raise DatasetPreparationError(
                f"{label_path}:{line_number} has unsupported class {source_class}"
            )
        if not all(math.isfinite(value) for value in coordinates):
            raise DatasetPreparationError(
                f"{label_path}:{line_number} contains a non-finite coordinate"
            )

        source_counts[source_class] += 1
        if coordinates[2] <= 0.0 or coordinates[3] <= 0.0:
            cleaning_counts["dropped_non_positive_size"] += 1
            continue

        x_center, y_center, width, height = coordinates
        x_min = x_center - width / 2.0
        y_min = y_center - height / 2.0
        x_max = x_center + width / 2.0
        y_max = y_center + height / 2.0
        clipped_x_min = max(0.0, x_min)
        clipped_y_min = max(0.0, y_min)
        clipped_x_max = min(1.0, x_max)
        clipped_y_max = min(1.0, y_max)

        if clipped_x_max <= clipped_x_min or clipped_y_max <= clipped_y_min:
            cleaning_counts["dropped_outside_image"] += 1
            continue
        if (
            clipped_x_min != x_min
            or clipped_y_min != y_min
            or clipped_x_max != x_max
            or clipped_y_max != y_max
        ):
            cleaning_counts["clipped_to_image_bounds"] += 1

        x_center = (clipped_x_min + clipped_x_max) / 2.0
        y_center = (clipped_y_min + clipped_y_max) / 2.0
        width = clipped_x_max - clipped_x_min
        height = clipped_y_max - clipped_y_min

        target_class = SOURCE_TO_TARGET_CLASS[source_class]
        target_counts[target_class] += 1
        transformed_lines.append(
            f"{target_class} {x_center:.10f} {y_center:.10f} "
            f"{width:.10f} {height:.10f}"
        )

    return transformed_lines, source_counts, target_counts, cleaning_counts


def _validate_source(source_root: Path) -> tuple[dict, dict]:
    source_data = source_root / "data"
    if not source_data.is_dir():
        raise DatasetPreparationError(f"Source data directory not found: {source_data}")

    manifests: dict = {}
    report = {
        "source": str(source_root.resolve()),
        "source_url": DATASET_SOURCE_URL,
        "license": "CC0: Public Domain",
        "source_classes": {"0": "smoke", "1": "fire"},
        "target_classes": {str(key): value for key, value in TARGET_CLASS_NAMES.items()},
        "class_mapping": {"0": 1, "1": 0},
        "splits": {},
        "source_box_counts": Counter(),
        "target_box_counts": Counter(),
        "cleaning_counts": Counter(),
    }

    for split in SPLITS:
        image_dir = source_data / split / "images"
        label_dir = source_data / split / "labels"
        if not image_dir.is_dir() or not label_dir.is_dir():
            raise DatasetPreparationError(
                f"Missing images/labels directories for split: {split}"
            )

        images = _files_by_stem(image_dir, IMAGE_EXTENSIONS)
        labels = _files_by_stem(label_dir, {".txt"})
        orphan_labels = sorted(set(labels) - set(images))
        if orphan_labels:
            sample = ", ".join(orphan_labels[:5])
            raise DatasetPreparationError(
                f"Split {split} has labels without images, for example: {sample}"
            )

        empty_labels = 0
        split_source_counts: Counter = Counter()
        split_target_counts: Counter = Counter()
        split_cleaning_counts: Counter = Counter()
        transformed_by_stem: dict[str, list[str]] = {}

        for stem, label_path in labels.items():
            lines, source_counts, target_counts, cleaning_counts = _transform_label(
                label_path
            )
            transformed_by_stem[stem] = lines
            split_source_counts.update(source_counts)
            split_target_counts.update(target_counts)
            split_cleaning_counts.update(cleaning_counts)
            if not lines:
                empty_labels += 1

        missing_labels = sorted(set(images) - set(labels))
        empty_labels += len(missing_labels)
        report["source_box_counts"].update(split_source_counts)
        report["target_box_counts"].update(split_target_counts)
        report["cleaning_counts"].update(split_cleaning_counts)
        report["splits"][split] = {
            "images": len(images),
            "source_label_files": len(labels),
            "missing_label_files": len(missing_labels),
            "empty_label_files": empty_labels,
            "source_box_counts": dict(sorted(split_source_counts.items())),
            "target_box_counts": dict(sorted(split_target_counts.items())),
            "cleaning_counts": dict(sorted(split_cleaning_counts.items())),
        }
        manifests[split] = {
            "images": images,
            "transformed_labels": transformed_by_stem,
        }

    report["source_box_counts"] = dict(sorted(report["source_box_counts"].items()))
    report["target_box_counts"] = dict(sorted(report["target_box_counts"].items()))
    report["cleaning_counts"] = dict(sorted(report["cleaning_counts"].items()))
    return manifests, report


def _write_dataset(staging_root: Path, manifests: dict, report: dict) -> None:
    for split in SPLITS:
        destination_images = staging_root / "images" / split
        destination_labels = staging_root / "labels" / split
        destination_images.mkdir(parents=True, exist_ok=True)
        destination_labels.mkdir(parents=True, exist_ok=True)

        images: dict[str, Path] = manifests[split]["images"]
        transformed_labels: dict[str, list[str]] = manifests[split][
            "transformed_labels"
        ]
        for index, (stem, source_image) in enumerate(images.items(), start=1):
            shutil.copy2(source_image, destination_images / source_image.name)
            label_lines = transformed_labels.get(stem, [])
            label_text = "\n".join(label_lines)
            if label_text:
                label_text += "\n"
            (destination_labels / f"{stem}.txt").write_text(
                label_text, encoding="utf-8"
            )
            if index % 2000 == 0 or index == len(images):
                print(f"  {split}: prepared {index}/{len(images)} images")

    yaml_text = "\n".join(
        [
            f'path: "{staging_root.resolve().as_posix()}"',
            "train: images/train",
            "val: images/val",
            "test: images/test",
            "nc: 2",
            "names:",
            "  0: fire",
            "  1: smoke",
            "",
        ]
    )
    (staging_root / "data.yaml").write_text(yaml_text, encoding="utf-8")
    (staging_root / "preparation_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def prepare_dataset(source_root: Path, output_root: Path) -> dict:
    source_root = source_root.resolve()
    output_root = output_root.resolve()
    staging_root = output_root.with_name(f"{output_root.name}.staging")

    if output_root.exists():
        raise DatasetPreparationError(
            f"Output already exists; refusing to overwrite: {output_root}"
        )
    if staging_root.exists():
        raise DatasetPreparationError(
            f"Staging directory already exists; inspect it first: {staging_root}"
        )

    print("Validating the complete source dataset...")
    manifests, report = _validate_source(source_root)
    report["output"] = str(output_root)
    output_root.parent.mkdir(parents=True, exist_ok=True)

    print("Writing the remapped dataset...")
    try:
        _write_dataset(staging_root, manifests, report)
        # data.yaml 必须引用最终目录，而不是临时写入目录。
        yaml_path = staging_root / "data.yaml"
        yaml_text = yaml_path.read_text(encoding="utf-8").replace(
            staging_root.resolve().as_posix(), output_root.resolve().as_posix(), 1
        )
        yaml_path.write_text(yaml_text, encoding="utf-8")
        staging_root.rename(output_root)
    except Exception:
        if staging_root.exists():
            shutil.rmtree(staging_root)
        raise

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return report


def build_parser() -> argparse.ArgumentParser:
    backend_root = Path(__file__).resolve().parents[1]
    default_output = backend_root / "datasets" / "fire_smoke" / "yolo_dataset"
    parser = argparse.ArgumentParser(
        description="Validate, reorganize, and remap the D-Fire YOLO dataset"
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Extracted source root containing data/ and data.yaml",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help=f"Destination dataset root (default: {default_output})",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        prepare_dataset(args.source, args.output)
    except DatasetPreparationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
