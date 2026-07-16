"""LangChain 检测 Tool 定义与安全边界测试。"""

import json
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
        service=service,
        stub_mode=True,
    )

    result = json.loads(
        _tools(runtime)["detect_single_image"].invoke(
            {"attachment_id": "attachment-1", "scene_id": 3}
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
        attachment_resolver=lambda attachment_id: None,
    )

    assert runtime.stub_mode is False


def test_real_single_tool_calls_business_service(tmp_path):
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
        attachment_resolver=lambda attachment_id: SimpleNamespace(
            file_name="fire.jpg", data=b"image-bytes"
        ),
        service=service,
        stub_mode=False,
    )

    result = json.loads(
        _tools(runtime)["detect_single_image"].invoke(
            {"attachment_id": "attachment-1", "scene_id": 3}
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


def test_real_tool_rejects_an_invalid_attachment_type(tmp_path):
    runtime = DetectionToolRuntime(
        user_id=7,
        db=MagicMock(),
        attachment_resolver=lambda attachment_id: SimpleNamespace(
            file_name="secret.txt", data=b"secret"
        ),
        service=MagicMock(),
        stub_mode=False,
    )

    with pytest.raises(ToolException, match="type is not valid"):
        _tools(runtime)["detect_single_image"].invoke(
            {"attachment_id": "attachment-1", "scene_id": 3}
        )


def test_zip_tool_reports_missing_backend_capability(tmp_path):
    runtime = DetectionToolRuntime(
        user_id=7,
        db=MagicMock(),
        attachment_resolver=lambda attachment_id: SimpleNamespace(
            file_name="images.zip", data=b"PK"
        ),
        service=object(),
        stub_mode=False,
    )

    with pytest.raises(ToolException, match="not implemented"):
        _tools(runtime)["detect_zip_images_file"].invoke(
            {"attachment_id": "attachment-1", "scene_id": 3}
        )
