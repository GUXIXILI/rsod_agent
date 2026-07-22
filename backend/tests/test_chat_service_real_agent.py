import json
import pytest
from unittest.mock import patch, MagicMock
from app.services.chat_service import chat_service


def test_run_agent_real_pre_detects_image_and_injects_summary_only():
    files = [{"type": "image", "url": "http://localhost:9000/test.jpg", "name": "test.jpg"}]
    with patch.object(chat_service, "_has_image_file", return_value=True), \
         patch.object(chat_service, "_extract_first_image_url", return_value="http://localhost:9000/test.jpg"), \
         patch.object(chat_service, "_extract_tool_result_summary", return_value="检测到 2 个火焰目标"), \
         patch("app.services.chat_service.detection_agent") as mock_agent, \
         patch("app.services.chat_service.concurrent.futures.ThreadPoolExecutor") as mock_executor:
            mock_agent.available = True
            mock_agent.chat = MagicMock(return_value={"output": "已检测到火情"})
            mock_executor.return_value.__enter__.return_value.submit.return_value.result.return_value = json.dumps({
                "summary": "检测到 2 个火焰目标",
                "annotated_image": "data:image/jpeg;base64,/9j/4AAQ..."
            })

            reply, tool_calls, tool_result, *_ = chat_service._run_agent_real("检测这张图片", history=[], files=files)

            # 应该主动调用一次 detect_single_image
            assert any(tc["tool"] == "detect_single_image" for tc in tool_calls)
            # 注入 prompt 的内容不应包含 base64
            prompt = mock_agent.chat.call_args[0][0]
            assert "data:image/jpeg;base64" not in prompt
            assert "检测到 2 个火焰目标" in prompt
