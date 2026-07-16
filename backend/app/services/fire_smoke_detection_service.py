"""
火灾烟雾 YOLO 推理与连续帧确认服务

核心功能：
1. FireSmokeDetectionService — 懒加载 YOLO 模型，按类别应用独立置信度阈值进行推理
2. TemporalConfirmationTracker — 连续帧确认追踪器，仅当某类别连续出现指定帧数后才确认
3. VideoConfirmationRegistry — 多视频流的短期连续帧确认状态注册表

数据类：
- Detection: 单个检测目标（类别、置信度、边界框）
- InferenceResult: 推理结果（检测列表 + 图像尺寸 + 推理耗时）
- ConfirmationState: 确认状态（连续帧数、是否确认、是否新确认）
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from threading import RLock
from time import monotonic
from typing import Any, Mapping, Sequence

from PIL import Image

from app.config.settings import settings
from app.core.logger import get_logger
from app.services.fire_smoke_constants import EXPECTED_CLASSES


# 后端根目录绝对路径
BACKEND_ROOT = Path(__file__).resolve().parents[2]

logger = get_logger(__name__)


@dataclass(frozen=True)
class Detection:
    """单个检测目标的数据类"""
    class_id: int
    class_name: str
    confidence: float
    bbox: list[float]  # [x1, y1, x2, y2]


@dataclass(frozen=True)
class InferenceResult:
    """推理结果的数据类"""
    detections: list[Detection]
    image_width: int
    image_height: int
    inference_time_ms: float

    def to_dict(self) -> dict[str, Any]:
        """将推理结果序列化为字典，供 API 响应使用"""
        return {
            "detections": [asdict(item) for item in self.detections],
            "image_width": self.image_width,
            "image_height": self.image_height,
            "inference_time_ms": self.inference_time_ms,
        }


@dataclass(frozen=True)
class ConfirmationState:
    """连续帧确认状态的数据类"""
    class_name: str
    consecutive_frames: int  # 当前连续出现帧数
    required_frames: int     # 所需的确认帧数
    confirmed: bool           # 是否已确认
    newly_confirmed: bool     # 是否本帧新确认（用于触发告警）


class FireSmokeDetectionService:
    """
    火灾烟雾检测服务

    懒加载单个 YOLO 模型，按类别应用独立置信度阈值进行推理。
    支持降级模式：当模型权重文件缺失时，服务不阻塞启动，
    而是将 available 标志设为 False，所有检测请求返回空结果。

    特性：
    - 线程安全：使用 RLock 保护模型加载和推理
    - 类别校验：启动时验证模型类别配置与 EXPECTED_CLASSES 一致
    - 独立阈值：fire 和 smoke 可设置不同的置信度阈值
    """

    def __init__(
        self,
        model_path: str | Path | None = None,
        device: str | None = None,
        model: Any | None = None,
    ) -> None:
        """
        初始化检测服务。

        Args:
            model_path: 模型权重文件路径，默认使用 settings.FIRE_SMOKE_MODEL_PATH
            device: 推理设备（"cpu" 或 "0"），默认使用 settings.FIRE_SMOKE_DEVICE
            model: 已加载的 YOLO 模型实例（测试场景使用），正常调用时传 None
        """
        configured_path = model_path or settings.FIRE_SMOKE_MODEL_PATH
        path = Path(configured_path).expanduser()
        self.model_path = path if path.is_absolute() else BACKEND_ROOT / path
        configured_device = (
            settings.FIRE_SMOKE_DEVICE if device is None else device
        )
        self.device = configured_device.strip() or None
        self._model = model
        self._lock = RLock()
        # 模型可用性标志：权重文件缺失时降级为 stub 模式，不阻塞服务启动
        # 仅在未显式传入 model 实例时检查权重文件（测试场景常传入 mock model）
        self.available: bool = True
        if model is None and not self.model_path.is_file():
            logger.warning(
                "火灾烟雾模型权重文件不存在: %s，服务将以降级模式运行（检测返回空结果）",
                self.model_path,
            )
            self.available = False
        elif model is not None:
            self._validate_model_classes(model)

    def _get_model(self) -> Any:
        """
        懒加载并返回 YOLO 模型实例（线程安全）。

        模型仅在首次调用时加载，之后复用缓存的实例。
        加载时自动校验模型类别配置。

        Returns:
            YOLO 模型实例

        Raises:
            FileNotFoundError: 模型权重文件不存在时抛出
        """
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
        """
        将 YOLO 模型的类别名称统一转换为 {int: str} 映射。

        YOLO 不同版本可能返回 dict 或 list 格式的类别名称，
        此方法统一处理两种格式，确保后续代码可安全使用。

        Args:
            names: YOLO 模型的 names 属性（dict 或 list）

        Returns:
            dict[int, str]: 类别 ID 到名称的映射

        Raises:
            ValueError: names 为空或格式无效时抛出
        """
        if isinstance(names, Mapping):
            return {int(key): str(value) for key, value in names.items()}
        if isinstance(names, Sequence) and not isinstance(names, (str, bytes)):
            return {index: str(value) for index, value in enumerate(names)}
        raise ValueError("YOLO model class names are missing or invalid")

    @classmethod
    def _validate_model_classes(cls, model: Any) -> None:
        """
        校验模型类别配置是否与预期一致。

        确保加载的模型确实是火灾烟雾检测模型（fire 和 smoke 两个类别），
        避免错误加载通用 COCO 模型导致检测结果异常。

        Args:
            model: YOLO 模型实例

        Raises:
            ValueError: 模型类别与 EXPECTED_CLASSES 不匹配时抛出
        """
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
        """
        对单张图片执行火焰/烟雾检测推理。

        流程：
        1. 降级检查：如果模型不可用，返回空结果
        2. 阈值校验：确保 fire 和 smoke 阈值均在 [0, 1] 范围内
        3. 模型推理：调用 YOLO model.predict() 执行前向传播
        4. 结果过滤：按类别独立阈值过滤低置信度检测框
        5. 耗时统计：汇总 preprocess + inference + postprocess 耗时

        Args:
            image: PIL Image 对象（RGB 格式）
            thresholds: 类别阈值映射，如 {"fire": 0.5, "smoke": 0.3}
            iou_threshold: NMS 非极大值抑制 IoU 阈值，默认 0.45
            image_size: 推理图像尺寸，默认 640

        Returns:
            InferenceResult: 包含检测列表、图像尺寸、推理耗时的结果对象

        Raises:
            ValueError: 阈值参数无效时抛出
            RuntimeError: YOLO 推理返回空结果时抛出
        """
        # 降级模式：权重缺失时返回 stub 结果（空检测列表），不抛异常
        if not self.available:
            width, height = image.size
            return InferenceResult(
                detections=[],
                image_width=int(width),
                image_height=int(height),
                inference_time_ms=0.0,
            )
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
        """
        校验并规范化检测阈值参数。

        确保 fire 和 smoke 的阈值都在 [0, 1] 范围内，
        且两个类别的阈值都必须提供。

        Args:
            thresholds: 原始阈值映射

        Returns:
            dict[str, float]: 规范化后的阈值映射

        Raises:
            ValueError: 阈值缺失或超出范围时抛出
        """
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
    """
    时序连续帧确认追踪器。

    仅当某个类别（fire/smoke）在连续帧中持续出现达到指定帧数后，
    才将该类别标记为"已确认"（confirmed）。
    如果某一帧该类别未出现，计数器立即重置为 0。

    用于减少视频检测中的误报：单帧误检不会触发告警，
    只有连续多帧检测到同一类别才认为是真实火情。

    注意：这是一个有状态对象，每个视频流应创建独立的实例。
    """

    def __init__(self, required_frames: Mapping[str, int]) -> None:
        """
        初始化确认追踪器。

        Args:
            required_frames: 各类别确认所需的连续帧数，如 {"fire": 3, "smoke": 5}

        Raises:
            ValueError: 任一类别所需帧数小于 1 时抛出
        """
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
        """
        根据当前帧的检测结果更新确认状态。

        对于每个类别：
        - 如果当前帧检测到该类别，连续帧计数器 +1
        - 如果当前帧未检测到该类别，连续帧计数器重置为 0
        - 当连续帧数 >= 所需帧数时，标记为 confirmed
        - 如果从"未确认"变为"已确认"，标记 newly_confirmed=True

        Args:
            detections: 当前帧的检测结果列表

        Returns:
            dict[str, ConfirmationState]: 各类别的确认状态
        """
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
    """注册表中每个视频流的追踪条目，包含追踪器和元数据"""
    tracker: TemporalConfirmationTracker  # 当前流的确认追踪器
    required_frames: dict[str, int]       # 确认所需的帧数配置
    last_seen: float                       # 最后活跃时间戳，用于超时清理


class VideoConfirmationRegistry:
    """
    多视频流确认状态注册表。

    为相互独立的视频流保存短期连续帧确认状态。
    每个视频流通过唯一的 stream_id 标识，拥有独立的 TemporalConfirmationTracker。

    特性：
    - 超时清理：超过 idle_timeout_seconds 未活跃的流自动释放
    - 线程安全：使用 RLock 保护内部状态
    - 自动重建：帧数配置变更时自动创建新的追踪器
    """

    def __init__(self, idle_timeout_seconds: float = 600.0) -> None:
        """
        初始化注册表。

        Args:
            idle_timeout_seconds: 空闲超时时间（秒），默认 600 秒（10 分钟）
        """
        self.idle_timeout_seconds = idle_timeout_seconds
        self._entries: dict[str, _TrackerEntry] = {}
        self._lock = RLock()

    def update(
        self,
        stream_id: str,
        detections: Sequence[Detection],
        required_frames: Mapping[str, int],
    ) -> dict[str, ConfirmationState]:
        """
        更新指定视频流的确认状态。

        流程：
        1. 清理过期流
        2. 查找或创建该流的追踪器（如果帧数配置变更则重建）
        3. 更新最后活跃时间
        4. 调用追踪器的 update() 方法更新确认状态

        Args:
            stream_id: 视频流唯一标识，格式为 "{user_id}:{stream_id}"
            detections: 当前帧的检测结果列表
            required_frames: 各类别确认所需的连续帧数

        Returns:
            dict[str, ConfirmationState]: 各类别的确认状态
        """
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
        """
        重置指定视频流的确认状态。

        从注册表中移除该流的追踪器，下次帧到来时会重新创建。
        用于用户手动重置或视频流重新开始时。

        Args:
            stream_id: 视频流唯一标识

        Returns:
            bool: 是否成功移除（流不存在时返回 False）
        """
        with self._lock:
            return self._entries.pop(stream_id, None) is not None

    def _remove_expired(self, now: float) -> None:
        """
        清理超过空闲超时时间的视频流（需在锁内调用）。

        遍历所有注册的视频流，删除 last_seen 超过
        idle_timeout_seconds 的条目，避免内存泄漏。

        Args:
            now: 当前时间戳（monotonic）
        """
        expired = [
            stream_id
            for stream_id, entry in self._entries.items()
            if now - entry.last_seen > self.idle_timeout_seconds
        ]
        for stream_id in expired:
            del self._entries[stream_id]


fire_smoke_detection_service = FireSmokeDetectionService()
video_confirmation_registry = VideoConfirmationRegistry()
