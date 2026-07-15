"""火灾烟雾 YOLO 推理与连续帧确认服务。"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from threading import RLock
from time import monotonic
from typing import Any, Mapping, Sequence

from PIL import Image

from app.config.settings import settings
from app.services.fire_smoke_constants import EXPECTED_CLASSES


BACKEND_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Detection:
    class_id: int
    class_name: str
    confidence: float
    bbox: list[float]


@dataclass(frozen=True)
class InferenceResult:
    detections: list[Detection]
    image_width: int
    image_height: int
    inference_time_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "detections": [asdict(item) for item in self.detections],
            "image_width": self.image_width,
            "image_height": self.image_height,
            "inference_time_ms": self.inference_time_ms,
        }


@dataclass(frozen=True)
class ConfirmationState:
    class_name: str
    consecutive_frames: int
    required_frames: int
    confirmed: bool
    newly_confirmed: bool


class FireSmokeDetectionService:
    """懒加载单个 YOLO 模型，并按类别应用独立置信度阈值。"""

    def __init__(
        self,
        model_path: str | Path | None = None,
        device: str | None = None,
        model: Any | None = None,
    ) -> None:
        configured_path = model_path or settings.FIRE_SMOKE_MODEL_PATH
        path = Path(configured_path).expanduser()
        self.model_path = path if path.is_absolute() else BACKEND_ROOT / path
        configured_device = (
            settings.FIRE_SMOKE_DEVICE if device is None else device
        )
        self.device = configured_device.strip() or None
        self._model = model
        self._lock = RLock()
        if model is not None:
            self._validate_model_classes(model)

    def _get_model(self) -> Any:
        with self._lock:
            if self._model is None:
                if not self.model_path.is_file():
                    raise FileNotFoundError(
                        f"Fire/smoke model not found: {self.model_path}"
                    )
                from ultralytics import YOLO

                self._model = YOLO(str(self.model_path))
                self._validate_model_classes(self._model)
            return self._model

    @staticmethod
    def _normalize_names(names: Any) -> dict[int, str]:
        if isinstance(names, Mapping):
            return {int(key): str(value) for key, value in names.items()}
        if isinstance(names, Sequence) and not isinstance(names, (str, bytes)):
            return {index: str(value) for index, value in enumerate(names)}
        raise ValueError("YOLO model class names are missing or invalid")

    @classmethod
    def _validate_model_classes(cls, model: Any) -> None:
        names = cls._normalize_names(getattr(model, "names", None))
        if names != EXPECTED_CLASSES:
            raise ValueError(
                "Fire/smoke model classes must be exactly "
                f"{EXPECTED_CLASSES}, got {names}"
            )

    def detect(
        self,
        image: Image.Image,
        thresholds: Mapping[str, float],
        iou_threshold: float = 0.45,
        image_size: int = 640,
    ) -> InferenceResult:
        normalized_thresholds = self._validate_thresholds(thresholds)
        model = self._get_model()
        predict_args: dict[str, Any] = {
            "source": image,
            "conf": min(normalized_thresholds.values()),
            "iou": iou_threshold,
            "imgsz": image_size,
            "verbose": False,
        }
        if self.device is not None:
            predict_args["device"] = self.device

        with self._lock:
            results = model.predict(**predict_args)
        if not results:
            raise RuntimeError("YOLO inference returned no result")

        result = results[0]
        names = self._normalize_names(result.names)
        detections: list[Detection] = []
        boxes = result.boxes
        if boxes is not None:
            xyxy_values = boxes.xyxy.cpu().tolist()
            confidence_values = boxes.conf.cpu().tolist()
            class_values = boxes.cls.cpu().tolist()
            for bbox, confidence, class_value in zip(
                xyxy_values, confidence_values, class_values
            ):
                class_id = int(class_value)
                class_name = names.get(class_id)
                if class_name not in normalized_thresholds:
                    continue
                if float(confidence) < normalized_thresholds[class_name]:
                    continue
                detections.append(
                    Detection(
                        class_id=class_id,
                        class_name=class_name,
                        confidence=float(confidence),
                        bbox=[float(value) for value in bbox],
                    )
                )

        height, width = result.orig_shape
        speed = getattr(result, "speed", {}) or {}
        inference_time_ms = sum(
            float(speed.get(stage, 0.0))
            for stage in ("preprocess", "inference", "postprocess")
        )
        return InferenceResult(
            detections=detections,
            image_width=int(width),
            image_height=int(height),
            inference_time_ms=inference_time_ms,
        )

    @staticmethod
    def _validate_thresholds(
        thresholds: Mapping[str, float],
    ) -> dict[str, float]:
        normalized = {
            class_name: float(thresholds[class_name])
            for class_name in EXPECTED_CLASSES.values()
            if class_name in thresholds
        }
        if set(normalized) != set(EXPECTED_CLASSES.values()):
            raise ValueError("Both fire and smoke thresholds are required")
        if any(value < 0.0 or value > 1.0 for value in normalized.values()):
            raise ValueError("Detection thresholds must be between 0 and 1")
        return normalized


class TemporalConfirmationTracker:
    """仅当某类别连续出现指定帧数后才确认该类别。"""

    def __init__(self, required_frames: Mapping[str, int]) -> None:
        self.required_frames = {
            class_name: int(required_frames[class_name])
            for class_name in EXPECTED_CLASSES.values()
        }
        if any(value < 1 for value in self.required_frames.values()):
            raise ValueError("Required frame counts must be at least 1")
        self._counts = {class_name: 0 for class_name in self.required_frames}
        self._confirmed = {
            class_name: False for class_name in self.required_frames
        }

    def update(
        self, detections: Sequence[Detection]
    ) -> dict[str, ConfirmationState]:
        present_classes = {item.class_name for item in detections}
        states: dict[str, ConfirmationState] = {}
        for class_name, required in self.required_frames.items():
            was_confirmed = self._confirmed[class_name]
            if class_name in present_classes:
                self._counts[class_name] += 1
            else:
                self._counts[class_name] = 0
            confirmed = self._counts[class_name] >= required
            self._confirmed[class_name] = confirmed
            states[class_name] = ConfirmationState(
                class_name=class_name,
                consecutive_frames=self._counts[class_name],
                required_frames=required,
                confirmed=confirmed,
                newly_confirmed=confirmed and not was_confirmed,
            )
        return states


@dataclass
class _TrackerEntry:
    tracker: TemporalConfirmationTracker
    required_frames: dict[str, int]
    last_seen: float


class VideoConfirmationRegistry:
    """为相互独立的视频流保存短期连续帧确认状态。"""

    def __init__(self, idle_timeout_seconds: float = 600.0) -> None:
        self.idle_timeout_seconds = idle_timeout_seconds
        self._entries: dict[str, _TrackerEntry] = {}
        self._lock = RLock()

    def update(
        self,
        stream_id: str,
        detections: Sequence[Detection],
        required_frames: Mapping[str, int],
    ) -> dict[str, ConfirmationState]:
        normalized_requirements = {
            class_name: int(required_frames[class_name])
            for class_name in EXPECTED_CLASSES.values()
        }
        now = monotonic()
        with self._lock:
            self._remove_expired(now)
            entry = self._entries.get(stream_id)
            if (
                entry is None
                or entry.required_frames != normalized_requirements
            ):
                entry = _TrackerEntry(
                    tracker=TemporalConfirmationTracker(
                        normalized_requirements
                    ),
                    required_frames=normalized_requirements,
                    last_seen=now,
                )
                self._entries[stream_id] = entry
            entry.last_seen = now
            return entry.tracker.update(detections)

    def reset(self, stream_id: str) -> bool:
        with self._lock:
            return self._entries.pop(stream_id, None) is not None

    def _remove_expired(self, now: float) -> None:
        expired = [
            stream_id
            for stream_id, entry in self._entries.items()
            if now - entry.last_seen > self.idle_timeout_seconds
        ]
        for stream_id in expired:
            del self._entries[stream_id]


fire_smoke_detection_service = FireSmokeDetectionService()
video_confirmation_registry = VideoConfirmationRegistry()
