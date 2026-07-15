"""LangChain 检测 Tool 定义与安全边界测试。"""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from langchain_core.tools import ToolException

from app.agent.tools.detection_tool import (
    DetectionToolRuntime,
    build_detection_tools,
)
from app.config.settings import settings


def _tools(runtime):
    return {item.name: item for item in build_detection_tools(runtime)}


def test_builds_four_tools_without_exposing_runtime_context(tmp_path):
    runtime = DetectionToolRuntime(
        user_id=7,
        db=MagicMock(),
        allowed_file_roots=(tmp_path,),
    )
    tools = _tools(runtime)

    assert set(tools) == {
        "detect_single_image",
        "detect_batch_images",
        "detect_zip_images_file",
        "detect_video_file",
    }
    assert "user_id" not in tools["detect_single_image"].args
    assert "db" not in tools["detect_single_image"].args


def test_stub_mode_returns_explicit_simulated_result(tmp_path):
    service = MagicMock()
    runtime = DetectionToolRuntime(
        user_id=7,
        db=MagicMock(),
        allowed_file_roots=(tmp_path,),
        service=service,
        stub_mode=True,
    )

    result = json.loads(
        _tools(runtime)["detect_single_image"].invoke(
            {"file_path": "not-created.jpg", "scene_id": 3}
        )
    )

    assert result["status"] == "simulated"
    assert result["stub"] is True
    service.detect_single.assert_not_called()


def test_runtime_reads_current_stub_setting(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "LLM_STUB_MODE", False)

    runtime = DetectionToolRuntime(
        user_id=7,
        db=MagicMock(),
        allowed_file_roots=(tmp_path,),
    )

    assert runtime.stub_mode is False


def test_real_single_tool_calls_business_service(tmp_path):
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    image_path = upload_root / "fire.jpg"
    image_path.write_bytes(b"image-bytes")
    task = SimpleNamespace(
        id=11,
        status="completed",
        fire_level="warning",
        fire_object_count=2,
        smoke_object_count=1,
        annotated_url="http://minio/annotated.jpg",
        error_message=None,
    )
    service = MagicMock()
    service.detect_single.return_value = task
    runtime = DetectionToolRuntime(
        user_id=7,
        db=MagicMock(),
        allowed_file_roots=(upload_root,),
        service=service,
        stub_mode=False,
    )

    result = json.loads(
        _tools(runtime)["detect_single_image"].invoke(
            {"file_path": str(image_path), "scene_id": 3}
        )
    )

    assert result["task_id"] == 11
    assert result["fire_level"] == "warning"
    assert result["fire_count"] == 2
    service.detect_single.assert_called_once()
    kwargs = service.detect_single.call_args.kwargs
    assert kwargs["user_id"] == 7
    assert kwargs["scene_id"] == 3
    assert kwargs["image_file"] == b"image-bytes"


def test_real_tool_rejects_path_outside_allowed_roots(tmp_path):
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    outside_path = tmp_path / "secret.jpg"
    outside_path.write_bytes(b"secret")
    runtime = DetectionToolRuntime(
        user_id=7,
        db=MagicMock(),
        allowed_file_roots=(upload_root,),
        service=MagicMock(),
        stub_mode=False,
    )

    with pytest.raises(ToolException, match="允许的上传目录"):
        _tools(runtime)["detect_single_image"].invoke(
            {"file_path": str(outside_path), "scene_id": 3}
        )


def test_zip_tool_reports_missing_backend_capability(tmp_path):
    zip_path = tmp_path / "images.zip"
    zip_path.write_bytes(b"PK")
    runtime = DetectionToolRuntime(
        user_id=7,
        db=MagicMock(),
        allowed_file_roots=(tmp_path,),
        service=object(),
        stub_mode=False,
    )

    with pytest.raises(ToolException, match="尚未实现"):
        _tools(runtime)["detect_zip_images_file"].invoke(
            {"file_path": str(zip_path), "scene_id": 3}
        )
