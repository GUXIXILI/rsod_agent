"""
检测工具单元测试

验证 LangChain @tool 装饰的检测工具返回格式，重点覆盖：
- detect_single_image 返回带标注图 URL/base64 的结构化 JSON
- 无目标时返回安全状态
- MinIO 上传失败时用 base64 兜底
"""
import base64
import io
import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from app.agent.tools.detection_tool import detect_single_image


def _make_jpeg_bytes(width=100, height=100) -> bytes:
    """生成一张最小 JPEG 图片字节"""
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def temp_image_file():
    """创建临时图片文件，测试结束后自动清理"""
    fd, path = tempfile.mkstemp(suffix=".jpg")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(_make_jpeg_bytes())
        yield path
    finally:
        if os.path.exists(path):
            os.unlink(path)


class TestDetectSingleImageTool:
    """detect_single_image 工具输出格式测试"""

    @patch("app.agent.tools.detection_tool.SessionLocal")
    @patch("app.agent.tools.detection_tool.detection_service")
    def test_returns_structured_json_with_annotated_url(
        self, mock_detection_service, mock_session_local, temp_image_file
    ):
        """检测到目标时，返回包含标注图 URL 的结构化 JSON"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        task = MagicMock()
        task.id = 1
        task.fire_object_count = 2
        task.smoke_object_count = 1
        task.fire_level = "danger"
        task.total_inference_time = 35.5
        task.annotated_url = "http://minio/test/annotated.jpg"
        task.original_url = "http://minio/test/original.jpg"
        task.annotated_image_base64 = None
        mock_detection_service.detect_single.return_value = task

        # 模拟无 DetectionResult 详情记录
        mock_db.query.return_value.filter.return_value.all.return_value = []

        result = detect_single_image.invoke({"image_path": temp_image_file})

        parsed = json.loads(result)
        assert parsed["fire_object_count"] == 2
        assert parsed["smoke_object_count"] == 1
        assert parsed["fire_level"] == "danger"
        assert parsed["annotated_image_url"] == "http://minio/test/annotated.jpg"
        assert parsed["inference_time"] == 35.5
        assert "summary" in parsed
        assert "检测完成" in parsed["summary"]

    @patch("app.agent.tools.detection_tool.SessionLocal")
    @patch("app.agent.tools.detection_tool.detection_service")
    def test_returns_base64_when_minio_upload_fails(
        self, mock_detection_service, mock_session_local, temp_image_file
    ):
        """标注图上传失败时，返回 base64 编码的标注图"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        task = MagicMock()
        task.id = 2
        task.fire_object_count = 1
        task.smoke_object_count = 0
        task.fire_level = "warning"
        task.total_inference_time = 20.0
        task.annotated_url = None
        task.original_url = "http://minio/test/original.jpg"
        # detection_service 会在任务上附加 base64 标注图
        task.annotated_image_base64 = base64.b64encode(_make_jpeg_bytes()).decode("utf-8")
        mock_detection_service.detect_single.return_value = task

        mock_db.query.return_value.filter.return_value.all.return_value = []

        result = detect_single_image.invoke({"image_path": temp_image_file})

        parsed = json.loads(result)
        assert parsed["fire_object_count"] == 1
        assert parsed["annotated_image_url"] is None
        # 必须有 base64 兜底图
        assert "annotated_image_base64" in parsed
        assert isinstance(parsed["annotated_image_base64"], str)
        assert len(parsed["annotated_image_base64"]) > 0

    @patch("app.agent.tools.detection_tool.SessionLocal")
    @patch("app.agent.tools.detection_tool.detection_service")
    def test_returns_safe_when_no_detections(
        self, mock_detection_service, mock_session_local, temp_image_file
    ):
        """未检测到目标时返回安全状态"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        task = MagicMock()
        task.id = 3
        task.fire_object_count = 0
        task.smoke_object_count = 0
        task.fire_level = "safe"
        task.total_inference_time = 15.0
        task.annotated_url = "http://minio/test/annotated_safe.jpg"
        task.original_url = "http://minio/test/original_safe.jpg"
        task.annotated_image_base64 = None
        mock_detection_service.detect_single.return_value = task

        mock_db.query.return_value.filter.return_value.all.return_value = []

        result = detect_single_image.invoke({"image_path": temp_image_file})

        parsed = json.loads(result)
        assert parsed["fire_object_count"] == 0
        assert parsed["smoke_object_count"] == 0
        assert parsed["fire_level"] == "safe"
        assert "未检测到" in parsed["summary"]

    @patch("app.agent.tools.detection_tool.SessionLocal")
    @patch("app.agent.tools.detection_tool.detection_service")
    def test_returns_error_json_when_file_not_found(
        self, mock_detection_service, mock_session_local, temp_image_file
    ):
        """本地图片不存在时返回 JSON 错误而不是抛出异常"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        # 让 detect_single 抛出 FileNotFoundError
        mock_detection_service.detect_single.side_effect = FileNotFoundError("文件不存在")

        result = detect_single_image.invoke({"image_path": temp_image_file})

        parsed = json.loads(result)
        assert "error" in parsed
        assert "文件不存在" in parsed["error"]

    def test_returns_error_json_when_empty_path(self):
        """空图片路径时直接返回 JSON 错误"""
        result = detect_single_image.invoke({"image_path": ""})
        parsed = json.loads(result)
        assert "error" in parsed
        assert "路径为空" in parsed["error"]

    @patch("app.agent.tools.detection_tool.SessionLocal")
    @patch("app.agent.tools.detection_tool.detection_service")
    def test_omits_base64_when_empty(
        self, mock_detection_service, mock_session_local, temp_image_file
    ):
        """当 annotated_image_base64 为空字符串时不应出现在返回 JSON 中"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        task = MagicMock()
        task.id = 4
        task.fire_object_count = 1
        task.smoke_object_count = 0
        task.fire_level = "warning"
        task.total_inference_time = 20.0
        task.annotated_url = "http://minio/test/annotated.jpg"
        task.original_url = "http://minio/test/original.jpg"
        task.annotated_image_base64 = ""
        mock_detection_service.detect_single.return_value = task

        mock_db.query.return_value.filter.return_value.all.return_value = []

        result = detect_single_image.invoke({"image_path": temp_image_file})

        parsed = json.loads(result)
        assert "annotated_image_base64" not in parsed
