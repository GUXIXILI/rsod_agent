"""火灾烟雾模型评估服务。"""

from collections.abc import Mapping, Sequence
import hashlib
import json
import math
from pathlib import Path

from ultralytics import YOLO
from app.entity.db_models import ModelVersion

from collections.abc import Mapping, Sequence
import math


EXPECTED_CLASS_MAPPING = {0: "fire", 1: "smoke"}


class ModelEvaluationError(ValueError):
    """模型评估结果无效。"""


def _normalize_class_names(names) -> dict[int, str]:
    """将Ultralytics类别名称统一转换为字典并校验类别顺序。"""
    if isinstance(names, Mapping):
        try:
            normalized = {int(class_id): str(name) for class_id, name in names.items()}
        except (TypeError, ValueError) as exc:
            raise ModelEvaluationError("Invalid class mapping") from exc
    elif isinstance(names, Sequence) and not isinstance(names, (str, bytes)):
        normalized = {
            class_id: str(name)
            for class_id, name in enumerate(names)
        }
    else:
        raise ModelEvaluationError("Invalid class mapping")

    if normalized != EXPECTED_CLASS_MAPPING:
        raise ModelEvaluationError(
            f"Unexpected class mapping: {normalized}; "
            f"expected {EXPECTED_CLASS_MAPPING}"
        )

    return normalized


def _metric_value(name: str, value) -> float:
    """将指标转换为有限的0到1浮点数。"""
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ModelEvaluationError(f"Invalid metric value: {name}") from exc

    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ModelEvaluationError(
            f"Metric {name} must be between 0 and 1"
        )

    return number


def build_evaluation_summary(metrics) -> dict:
    """从Ultralytics验证结果提取数据库需要的评估指标。"""
    box_metrics = getattr(metrics, "box", None)
    if box_metrics is None:
        raise ModelEvaluationError(
            "Evaluation result does not contain box metrics"
        )

    class_names = _normalize_class_names(
        getattr(metrics, "names", None)
    )

    try:
        class_maps = list(box_metrics.maps)
    except (AttributeError, TypeError) as exc:
        raise ModelEvaluationError(
            "Evaluation result does not contain per-class metrics"
        ) from exc

    if len(class_maps) != len(class_names):
        raise ModelEvaluationError(
            "Evaluation class metric count does not match class mapping"
        )

    per_class_ap = {
        class_names[class_id]: _metric_value(
            f"{class_names[class_id]} mAP50-95",
            class_maps[class_id],
        )
        for class_id in sorted(class_names)
    }

    return {
        "precision": _metric_value("precision", box_metrics.mp),
        "recall": _metric_value("recall", box_metrics.mr),
        "map50": _metric_value("map50", box_metrics.map50),
        "map50_95": _metric_value("map50_95", box_metrics.map),
        "per_class_ap": per_class_ap,
    }

def _sha256(file_path: Path) -> str:
    """分块计算文件SHA256，避免一次性读取大型模型。"""
    digest = hashlib.sha256()
    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evaluate_model(
    model_path: str | Path,
    data_path: str | Path,
    output_dir: str | Path,
    split: str = "val",
    imgsz: int = 640,
    batch: int = 16,
    device: str = "cpu",
) -> dict:
    """运行YOLO验证，生成指标报告和混淆矩阵。"""
    resolved_model = Path(model_path).expanduser().resolve()
    resolved_data = Path(data_path).expanduser().resolve()
    resolved_output = Path(output_dir).expanduser().resolve()

    if not resolved_model.is_file():
        raise ModelEvaluationError(
            f"Model file does not exist: {resolved_model}"
        )
    if not resolved_data.is_file():
        raise ModelEvaluationError(
            f"Dataset configuration does not exist: {resolved_data}"
        )
    if split not in {"val", "test"}:
        raise ModelEvaluationError("split must be val or test")
    if imgsz < 320 or imgsz % 32 != 0:
        raise ModelEvaluationError(
            "imgsz must be at least 320 and divisible by 32"
        )
    if batch <= 0:
        raise ModelEvaluationError("batch must be greater than zero")

    resolved_output.parent.mkdir(parents=True, exist_ok=True)

    model = YOLO(str(resolved_model))
    metrics = model.val(
        data=str(resolved_data),
        split=split,
        imgsz=imgsz,
        batch=batch,
        device=device,
        workers=0,
        plots=True,
        project=str(resolved_output.parent),
        name=resolved_output.name,
        exist_ok=False,
        verbose=False,
    )

    summary = build_evaluation_summary(metrics)
    save_dir = Path(
        getattr(metrics, "save_dir", resolved_output)
    ).resolve()

    confusion_matrix = save_dir / "confusion_matrix.png"
    normalized_confusion_matrix = (
        save_dir / "confusion_matrix_normalized.png"
    )

    if not confusion_matrix.is_file():
        raise ModelEvaluationError(
            f"Confusion matrix was not generated: {confusion_matrix}"
        )
    if not normalized_confusion_matrix.is_file():
        raise ModelEvaluationError(
            "Normalized confusion matrix was not generated: "
            f"{normalized_confusion_matrix}"
        )

    report = {
        "model": str(resolved_model),
        "model_sha256": _sha256(resolved_model),
        "data": str(resolved_data),
        "split": split,
        "imgsz": imgsz,
        "batch": batch,
        "device": device,
        "metrics": summary,
        "artifacts": {
            "output_directory": str(save_dir),
            "confusion_matrix": str(confusion_matrix),
            "confusion_matrix_normalized": str(
                normalized_confusion_matrix
            ),
        },
    }

    (save_dir / "evaluation.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report


def _validated_report_metrics(report: dict) -> dict:
    """校验准备写入数据库的评估指标。"""
    if not isinstance(report, Mapping):
        raise ModelEvaluationError("Evaluation report must be a mapping")

    metrics = report.get("metrics")
    if not isinstance(metrics, Mapping):
        raise ModelEvaluationError(
            "Evaluation report does not contain metrics"
        )

    per_class_ap = metrics.get("per_class_ap")
    if not isinstance(per_class_ap, Mapping):
        raise ModelEvaluationError(
            "Evaluation report does not contain per-class AP"
        )

    expected_names = tuple(EXPECTED_CLASS_MAPPING.values())
    if set(per_class_ap) != set(expected_names):
        raise ModelEvaluationError(
            "Evaluation per-class AP does not match fire/smoke classes"
        )

    return {
        "precision": _metric_value(
            "precision", metrics.get("precision")
        ),
        "recall": _metric_value(
            "recall", metrics.get("recall")
        ),
        "map50": _metric_value(
            "map50", metrics.get("map50")
        ),
        "map50_95": _metric_value(
            "map50_95", metrics.get("map50_95")
        ),
        "per_class_ap": {
            class_name: _metric_value(
                f"{class_name} AP",
                per_class_ap[class_name],
            )
            for class_name in expected_names
        },
    }


def save_evaluation_result(
    db,
    model_version_id: int,
    report: dict,
) -> ModelVersion:
    """将模型评估结果安全写入ModelVersion记录。"""
    model_version = (
        db.query(ModelVersion)
        .filter(ModelVersion.id == model_version_id)
        .first()
    )
    if model_version is None:
        raise ModelEvaluationError(
            f"Model version not found: {model_version_id}"
        )

    reported_model = report.get("model")
    if not reported_model:
        raise ModelEvaluationError(
            "Evaluation report does not contain model path"
        )

    stored_path = Path(
        model_version.model_path
    ).expanduser().resolve()
    reported_path = Path(
        str(reported_model)
    ).expanduser().resolve()

    if stored_path != reported_path:
        raise ModelEvaluationError(
            "Evaluated model path does not match model version"
        )
    if not stored_path.is_file():
        raise ModelEvaluationError(
            f"Stored model file does not exist: {stored_path}"
        )

    metrics = _validated_report_metrics(report)

    model_version.precision = metrics["precision"]
    model_version.recall = metrics["recall"]
    model_version.map50 = metrics["map50"]
    model_version.map50_95 = metrics["map50_95"]
    model_version.per_class_ap = metrics["per_class_ap"]
    model_version.file_size = stored_path.stat().st_size

    try:
        db.commit()
        db.refresh(model_version)
    except Exception:
        db.rollback()
        raise

    return model_version


def evaluate_and_save_model(
    db,
    model_version_id: int,
    data_path: str | Path,
    output_dir: str | Path,
    split: str = "val",
    imgsz: int = 640,
    batch: int = 16,
    device: str = "cpu",
) -> tuple[ModelVersion, dict]:
    """使用数据库记录的模型路径执行评估并保存指标。"""
    model_version = (
        db.query(ModelVersion)
        .filter(ModelVersion.id == model_version_id)
        .first()
    )
    if model_version is None:
        raise ModelEvaluationError(
            f"Model version not found: {model_version_id}"
        )

    model_path = Path(model_version.model_path)

    report = evaluate_model(
        model_path=model_path,
        data_path=Path(data_path),
        output_dir=Path(output_dir),
        split=split,
        imgsz=imgsz,
        batch=batch,
        device=device,
    )

    updated = save_evaluation_result(
        db,
        model_version_id=model_version_id,
        report=report,
    )
    return updated, report