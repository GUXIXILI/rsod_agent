from types import SimpleNamespace

import pytest

from app.services.model_evaluation_service import (
    ModelEvaluationError,
    build_evaluation_summary,
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