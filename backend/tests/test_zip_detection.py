"""
ZIP 解压检测功能测试

测试 DetectionService.detect_zip 方法：
- 合法 ZIP（含图片）→ 调用 detect_batch 返回结果
- 空 ZIP → ValueError
- ZIP 中无图片 → ValueError
- ZIP 炸弹防护（超大小限制）→ ValueError
"""
import io
import zipfile
from unittest.mock import MagicMock, patch

import pytest


def _make_zip(file_map: dict[str, bytes]) -> bytes:
    """辅助：将 {filename: bytes} 打包为 ZIP 字节"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in file_map.items():
            zf.writestr(name, data)
    return buf.getvalue()


# 1x1 PNG 最小合法图片
_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
    b"\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00"
    b"\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


class TestDetectZipValid:
    """合法 ZIP → 正确调用 detect_single"""

    @patch("app.services.detection_service.DetectionService.detect_single")
    def test_detect_zip_valid(self, mock_single, db_session):
        from app.services.detection_service import DetectionService

        svc = DetectionService()
        mock_single.return_value = MagicMock(id=1)

        zip_bytes = _make_zip({"photo1.png": _TINY_PNG, "photo2.png": _TINY_PNG})
        result = svc.detect_zip(db_session, user_id=1, scene_id=1, zip_bytes=zip_bytes, filename="test.zip")

        assert len(result) == 2
        assert mock_single.call_count == 2


class TestDetectZipEmpty:
    """空 ZIP → 返回空列表"""

    def test_detect_zip_empty(self, db_session):
        from app.services.detection_service import DetectionService

        svc = DetectionService()
        empty_zip = _make_zip({})
        result = svc.detect_zip(db_session, user_id=1, scene_id=1, zip_bytes=empty_zip, filename="empty.zip")
        assert isinstance(result, list)
        assert len(result) == 0


class TestDetectZipNoImages:
    """ZIP 中只有非图片文件 → 返回空列表"""

    def test_detect_zip_no_images(self, db_session):
        from app.services.detection_service import DetectionService

        svc = DetectionService()
        zip_bytes = _make_zip({"readme.txt": b"hello world", "data.csv": b"a,b,c"})
        result = svc.detect_zip(db_session, user_id=1, scene_id=1, zip_bytes=zip_bytes, filename="noimg.zip")
        assert isinstance(result, list)
        assert len(result) == 0


class TestDetectZipOversize:
    """ZIP 文件超过大小限制 → HTTPException 413"""

    @patch("app.services.detection_service.settings")
    def test_detect_zip_oversize(self, mock_settings, db_session):
        from app.services.detection_service import DetectionService
        from fastapi import HTTPException

        mock_settings.ZIP_MAX_SIZE_MB = 1  # 1MB 限制

        svc = DetectionService()
        # 创建一个 2MB 的假数据（超过 1MB 限制）
        large_data = b"x" * (2 * 1024 * 1024)

        with pytest.raises(HTTPException, match="ZIP 文件超过最大限制"):
            svc.detect_zip(db_session, user_id=1, scene_id=1, zip_bytes=large_data, filename="big.zip")
