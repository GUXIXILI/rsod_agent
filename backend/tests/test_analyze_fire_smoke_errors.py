from pathlib import Path

import pytest

from tools.analyze_fire_smoke_errors import (
    ImageRecord,
    Prediction,
    box_iou,
    evaluate_records,
    match_class,
    parse_thresholds,
    recommend_threshold,
)


def test_box_iou_for_identical_and_disjoint_boxes():
    box = (10.0, 10.0, 30.0, 30.0)

    assert box_iou(box, box) == pytest.approx(1.0)
    assert box_iou(box, (40.0, 40.0, 50.0, 50.0)) == 0.0


def test_match_class_counts_duplicate_prediction_as_false_positive():
    ground_truths = [(0.0, 0.0, 10.0, 10.0)]
    predictions = [
        Prediction(0, 0.9, (0.0, 0.0, 10.0, 10.0)),
        Prediction(0, 0.8, (0.0, 0.0, 10.0, 10.0)),
    ]

    result = match_class(ground_truths, predictions, 0.5, 0.5)

    assert result.true_positives == 1
    assert result.false_positives == 1
    assert result.false_negatives == 0


def test_evaluate_records_reports_threshold_tradeoff():
    record = ImageRecord(
        image_path=Path("sample.jpg"),
        ground_truths=(
            (0, (0.0, 0.0, 10.0, 10.0)),
            (0, (20.0, 20.0, 30.0, 30.0)),
        ),
        predictions=(
            Prediction(0, 0.9, (0.0, 0.0, 10.0, 10.0)),
            Prediction(0, 0.7, (40.0, 40.0, 50.0, 50.0)),
            Prediction(0, 0.4, (20.0, 20.0, 30.0, 30.0)),
        ),
    )

    rows = evaluate_records([record], [0.5, 0.3], {0: "fire"}, 0.5)
    high_threshold = next(row for row in rows if row["threshold"] == 0.5)
    low_threshold = next(row for row in rows if row["threshold"] == 0.3)

    assert high_threshold["precision"] == pytest.approx(0.5)
    assert high_threshold["recall"] == pytest.approx(0.5)
    assert low_threshold["precision"] == pytest.approx(2 / 3)
    assert low_threshold["recall"] == pytest.approx(1.0)


def test_evaluate_records_reports_negative_image_alarm_rate():
    record = ImageRecord(
        image_path=Path("negative.jpg"),
        ground_truths=(),
        predictions=(Prediction(0, 0.8, (0.0, 0.0, 10.0, 10.0)),),
    )

    row = evaluate_records([record], [0.5], {0: "fire"}, 0.5)[0]

    assert row["negative_images"] == 1
    assert row["negative_alarm_images"] == 1
    assert row["negative_alarm_rate"] == pytest.approx(1.0)
    assert row["negative_predictions_per_image"] == pytest.approx(1.0)


def test_recommend_threshold_maximizes_recall_with_precision_floor():
    rows = [
        {"class_id": 0, "threshold": 0.1, "precision": 0.6, "recall": 0.9, "f1": 0.72},
        {"class_id": 0, "threshold": 0.2, "precision": 0.7, "recall": 0.8, "f1": 0.75},
        {"class_id": 0, "threshold": 0.3, "precision": 0.8, "recall": 0.7, "f1": 0.75},
    ]

    recommendation = recommend_threshold(rows, class_id=0, minimum_precision=0.65)

    assert recommendation is not None
    assert recommendation["threshold"] == 0.2


def test_parse_thresholds_sorts_and_deduplicates():
    assert parse_thresholds("0.25,0.10,0.25") == (0.1, 0.25)


def test_parse_thresholds_rejects_out_of_range_values():
    with pytest.raises(Exception, match="range"):
        parse_thresholds("0.0,0.5")
