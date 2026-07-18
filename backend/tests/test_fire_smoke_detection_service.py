from types import SimpleNamespace

from PIL import Image

from app.services.fire_smoke_detection_service import (
    Detection,
    FireSmokeDetectionService,
    TemporalConfirmationTracker,
    VideoConfirmationRegistry,
)


class FakeTensor:
    def __init__(self, values):
        self.values = values

    def cpu(self):
        return self

    def tolist(self):
        return self.values


class FakeModel:
    names = {0: "fire", 1: "smoke"}

    def __init__(self):
        self.predict_args = None

    def predict(self, **kwargs):
        self.predict_args = kwargs
        boxes = SimpleNamespace(
            xyxy=FakeTensor(
                [
                    [1, 2, 10, 20],
                    [2, 3, 11, 21],
                    [3, 4, 12, 22],
                    [4, 5, 13, 23],
                ]
            ),
            conf=FakeTensor([0.24, 0.26, 0.19, 0.21]),
            cls=FakeTensor([0, 0, 1, 1]),
        )
        return [
            SimpleNamespace(
                names=self.names,
                boxes=boxes,
                orig_shape=(100, 200),
                speed={
                    "preprocess": 1.0,
                    "inference": 2.0,
                    "postprocess": 3.0,
                },
            )
        ]


def detection(class_name):
    class_id = 0 if class_name == "fire" else 1
    return Detection(class_id, class_name, 0.9, [0.0, 0.0, 1.0, 1.0])


def test_detect_applies_independent_class_thresholds():
    model = FakeModel()
    service = FireSmokeDetectionService(model=model, device="cpu")

    result = service.detect(
        Image.new("RGB", (200, 100)),
        thresholds={"fire": 0.25, "smoke": 0.20},
    )

    assert [item.class_name for item in result.detections] == ["fire", "smoke"]
    assert [item.confidence for item in result.detections] == [0.26, 0.21]
    assert result.image_width == 200
    assert result.image_height == 100
    assert result.inference_time_ms == 6.0
    assert model.predict_args["conf"] == 0.20
    assert model.predict_args["device"] == "cpu"


def test_temporal_confirmation_requires_consecutive_frames():
    tracker = TemporalConfirmationTracker({"fire": 3, "smoke": 2})

    first = tracker.update([detection("fire")])
    second = tracker.update([detection("fire")])
    reset = tracker.update([])
    tracker.update([detection("fire"), detection("smoke")])
    tracker.update([detection("fire"), detection("smoke")])
    confirmed = tracker.update([detection("fire")])

    assert not first["fire"].confirmed
    assert not second["fire"].confirmed
    assert reset["fire"].consecutive_frames == 0
    assert confirmed["fire"].confirmed
    assert confirmed["fire"].newly_confirmed
    assert not confirmed["smoke"].confirmed


def test_registry_keeps_streams_independent_and_can_reset():
    registry = VideoConfirmationRegistry()
    requirements = {"fire": 2, "smoke": 2}

    registry.update("user-a:cam-1", [detection("fire")], requirements)
    cam_1 = registry.update("user-a:cam-1", [detection("fire")], requirements)
    cam_2 = registry.update("user-a:cam-2", [detection("fire")], requirements)

    assert cam_1["fire"].confirmed
    assert not cam_2["fire"].confirmed
    assert registry.reset("user-a:cam-1")
    assert not registry.reset("user-a:cam-1")
