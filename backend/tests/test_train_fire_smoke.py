from argparse import Namespace
from pathlib import Path

import pytest
import yaml

from tools.train_fire_smoke import (
    TrainingConfigurationError,
    resolve_run_name,
    validate_dataset_yaml,
    validate_numeric_arguments,
)


def _write_dataset_yaml(tmp_path: Path, names=None, nc=2) -> Path:
    dataset_root = tmp_path / "dataset"
    for split in ("train", "val", "test"):
        (dataset_root / "images" / split).mkdir(parents=True)
    data_yaml = dataset_root / "data.yaml"
    data_yaml.write_text(
        yaml.safe_dump(
            {
                "path": str(dataset_root),
                "train": "images/train",
                "val": "images/val",
                "test": "images/test",
                "nc": nc,
                "names": names if names is not None else {0: "fire", 1: "smoke"},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return data_yaml


def _numeric_args(**overrides) -> Namespace:
    values = {
        "epochs": 50,
        "batch": 16,
        "imgsz": 640,
        "patience": 10,
        "fraction": 1.0,
        "workers": 0,
        "save_period": 5,
    }
    values.update(overrides)
    return Namespace(**values)


def test_validate_dataset_yaml_accepts_expected_classes(tmp_path):
    result = validate_dataset_yaml(_write_dataset_yaml(tmp_path))

    assert result["class_names"] == {0: "fire", 1: "smoke"}
    assert set(result["splits"]) == {"train", "val", "test"}


def test_validate_dataset_yaml_rejects_reversed_classes(tmp_path):
    data_yaml = _write_dataset_yaml(tmp_path, names={0: "smoke", 1: "fire"})

    with pytest.raises(TrainingConfigurationError, match="Expected class mapping"):
        validate_dataset_yaml(data_yaml)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"epochs": 0}, "epochs"),
        ({"batch": 0}, "batch"),
        ({"imgsz": 641}, "imgsz"),
        ({"fraction": 0.0}, "fraction"),
        ({"workers": -1}, "workers"),
        ({"save_period": 0}, "save-period"),
    ],
)
def test_validate_numeric_arguments_rejects_invalid_values(overrides, message):
    with pytest.raises(TrainingConfigurationError, match=message):
        validate_numeric_arguments(_numeric_args(**overrides))


def test_resolve_run_name_is_reproducible():
    args = Namespace(
        name=None,
        model=Path("models/yolo11n.pt"),
        epochs=50,
        batch=16,
        seed=42,
    )

    assert resolve_run_name(args) == "yolo11n_e50_b16_s42"
