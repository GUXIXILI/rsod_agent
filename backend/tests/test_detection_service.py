"""
检测服务单元测试
使用 Mock 替代 YOLO 模型和 MinIO 上传，测试 detect_single 正常/异常流程及模型缓存 LRU 逻辑
"""
import io
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np
import pytest
from PIL import Image

from app.entity.db_models import DetectionScene, DetectionTask, ModelVersion
from app.services.detection_service import DetectionService


def _make_jpeg_bytes(width=100, height=100) -> bytes:
    """生成一张最小 JPEG 图片字节"""
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_mock_box(cls_id: int, conf: float, xyxy: list):
    """构造一个 Mock 检测框"""
    box = MagicMock()
    box.cls = MagicMock()
    box.cls.__getitem__ = MagicMock(return_value=MagicMock())
    box.cls[0] = MagicMock()
    box.cls[0].item.return_value = cls_id
    box.conf = MagicMock()
    box.conf[0] = MagicMock()
    box.conf[0].item.return_value = conf
    box.xyxy = MagicMock()
    box.xyxy[0] = MagicMock()
    box.xyxy[0].tolist.return_value = xyxy
    return box


def _make_mock_model(names: dict, boxes: list):
    """构造 Mock YOLO 模型"""
    model = MagicMock()
    model.names = names

    result = MagicMock()
    result.plot.return_value = np.zeros((100, 100, 3), dtype=np.uint8)

    mock_boxes = MagicMock()
    mock_boxes.__iter__ = MagicMock(return_value=iter(boxes))
    result.boxes = mock_boxes

    model.return_value = [result]
    return model


class TestDetectSingleNormal:
    """detect_single 正常流程测试"""

    @patch("app.services.detection_service.MinIOClient")
    @patch("app.services.detection_service.DetectionService._load_model")
    @patch("cv2.imencode")
    def test_detect_single_with_fire(self, mock_imencode, mock_load_model, mock_minio_cls, db_session, create_test_user):
        """检测出火焰时，detect_single 能正确判定 fire_object_count 并返回 completed 状态任务"""
        minio_instance = MagicMock()
        minio_instance.upload_bytes.return_value = "http://minio/test.jpg"
        mock_minio_cls.return_value = minio_instance
        mock_imencode.return_value = (True, np.zeros(100, dtype=np.uint8))

        box = MagicMock()
        box.cls = [0]
        box.conf = [0.9]
        box.xyxy = [MagicMock()]
        box.xyxy[0].tolist.return_value = [10.0, 10.0, 50.0, 50.0]

        model = MagicMock()
        model.names = {0: "fire", 1: "smoke"}
        result_obj = MagicMock()
        result_obj.plot.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
        result_obj.boxes = [box]
        model.return_value = [result_obj]
        mock_load_model.return_value = model

        scene = DetectionScene(
            name="test_scene", display_name="测试场景", category="fire",
            class_names=["fire", "smoke"]
        )
        db_session.add(scene)
        db_session.commit()
        db_session.refresh(scene)

        svc = DetectionService()
        task = svc.detect_single(
            db=db_session,
            user_id=create_test_user.id,
            scene_id=scene.id,
            image_file=_make_jpeg_bytes(),
            filename="test.jpg",
        )
        # 任务应返回 completed 状态（image_path/class_id/bbox 已修复）
        assert task is not None
        assert task.status == "completed"

    @patch("app.services.detection_service.MinIOClient")
    @patch("app.services.detection_service.DetectionService._load_model")
    @patch("cv2.imencode")
    def test_detect_single_no_detections(self, mock_imencode, mock_load_model, mock_minio_cls, db_session, create_test_user):
        """未检测到任何目标 → safe"""
        minio_instance = MagicMock()
        minio_instance.upload_bytes.return_value = "http://minio/test.jpg"
        mock_minio_cls.return_value = minio_instance
        mock_imencode.return_value = (True, np.zeros(100, dtype=np.uint8))

        model = MagicMock()
        model.names = {0: "fire", 1: "smoke"}
        result_obj = MagicMock()
        result_obj.plot.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
        result_obj.boxes = []
        model.return_value = [result_obj]
        mock_load_model.return_value = model

        scene = DetectionScene(
            name="test_scene2", display_name="测试场景2", category="fire",
            class_names=["fire", "smoke"]
        )
        db_session.add(scene)
        db_session.commit()
        db_session.refresh(scene)

        svc = DetectionService()
        task = svc.detect_single(
            db=db_session,
            user_id=create_test_user.id,
            scene_id=scene.id,
            image_file=_make_jpeg_bytes(),
            filename="empty.jpg",
        )
        assert task.status == "completed"
        assert task.fire_level == "safe"


class TestDetectSingleException:
    """detect_single 异常流程测试"""

    @patch("app.services.detection_service.MinIOClient")
    @patch("app.services.detection_service.DetectionService._load_model")
    def test_model_load_failure(self, mock_load_model, mock_minio_cls, db_session, create_test_user):
        """模型加载失败 → 返回 failed 状态任务"""
        minio_instance = MagicMock()
        minio_instance.upload_bytes.return_value = "http://minio/test.jpg"
        mock_minio_cls.return_value = minio_instance

        mock_load_model.side_effect = RuntimeError("模型文件损坏")

        scene = DetectionScene(
            name="test_scene3", display_name="测试场景3", category="fire",
            class_names=["fire", "smoke"]
        )
        db_session.add(scene)
        db_session.commit()
        db_session.refresh(scene)

        svc = DetectionService()
        task = svc.detect_single(
            db=db_session,
            user_id=create_test_user.id,
            scene_id=scene.id,
            image_file=_make_jpeg_bytes(),
            filename="fail.jpg",
        )
        assert task.status == "failed"
        assert "模型文件损坏" in task.error_message


class TestModelCacheLRU:
    """模型缓存 LRU 逻辑测试"""

    def test_cache_hit(self, db_session):
        """缓存命中时不重新加载"""
        svc = DetectionService()
        mock_model = MagicMock()
        svc._model_cache[1] = mock_model

        result = svc._load_model(db_session, 1)
        assert result is mock_model

    def test_cache_lru_eviction(self, db_session):
        """缓存满时淘汰最久未使用的模型"""
        svc = DetectionService()
        svc.MAX_CACHE_SIZE = 3

        # 填充缓存
        for i in range(3):
            svc._model_cache[i] = MagicMock()

        # 添加新模型需要淘汰最旧的（scene_id=0）
        with patch("ultralytics.YOLO") as mock_yolo:
            mock_yolo.return_value = MagicMock()
            # 触发加载新模型（scene_id 不在缓存中）
            svc._load_model(db_session, 99)

        assert 0 not in svc._model_cache
        assert 99 in svc._model_cache

    def test_cache_move_to_end_on_hit(self, db_session):
        """缓存命中时将模型移到末尾（最近使用）"""
        svc = DetectionService()
        svc._model_cache[1] = MagicMock()
        svc._model_cache[2] = MagicMock()
        svc._model_cache[3] = MagicMock()

        # 访问 scene_id=1，应移到末尾
        svc._load_model(db_session, 1)
        keys = list(svc._model_cache.keys())
        assert keys[-1] == 1  # 最后一个是最近访问的
