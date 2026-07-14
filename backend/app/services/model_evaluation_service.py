"""火灾烟雾模型评估服务。"""

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