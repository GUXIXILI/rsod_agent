"""
Agent 智能体测试

测试检测智能体相关功能：
- Agent 初始化失败时 available=False
- 4 个 @tool 函数可正常导入
- Agent 不可用时 chat_service 降级为 _call_llm
"""
from unittest.mock import MagicMock, patch, AsyncMock

import pytest


class TestAgentInitFallback:
    """Agent 初始化失败时应设置 available=False"""

    @patch("app.agent.detection_agent.create_openai_tools_agent", side_effect=Exception("mock init failure"))
    @patch("app.agent.detection_agent.ChatOpenAI")
    def test_agent_init_fallback(self, mock_llm_cls, mock_create_agent):
        """Agent 构造异常 → available=False, executor=None"""
        from app.agent.detection_agent import DetectionAgent

        agent = DetectionAgent()
        assert agent.available is False
        assert agent.executor is None


class TestToolDefinitions:
    """4 个 @tool 函数可正常导入"""

    def test_tool_definitions(self):
        """tools.py 中应导出 4 个工具函数"""
        from app.agent.tools import (
            detect_single_image,
            detect_batch_images,
            detect_zip_images_file,
            detect_video_file,
        )
        # 每个工具应有 name 属性（@tool 装饰器设置）
        assert detect_single_image.name == "detect_single_image"
        assert detect_batch_images.name == "detect_batch_images"
        assert detect_zip_images_file.name == "detect_zip_images_file"
        assert detect_video_file.name == "detect_video_file"


class TestChatFallbackToStub:
    """Agent 不可用时 chat_service 应降级为 _run_agent_stub"""

    @patch("app.agent.detection_agent.detection_agent")
    def test_chat_fallback_to_stub(self, mock_agent, db_session, create_test_user):
        from app.services.chat_service import ChatService

        svc = ChatService()

        # 模拟 Agent 不可用
        mock_agent.available = False

        # Mock _run_agent 返回 stub 结果（rsod_agent 的降级路径）
        with patch.object(svc, "_run_agent", return_value=("AI 回复内容", None, None, 0, 0)) as mock_run:
            # 创建一个会话
            session = svc.create_session(db_session, create_test_user.id, "测试会话")

            # 发送消息
            result = svc.send_message(
                db=db_session,
                session_id=session.id,
                user_id=create_test_user.id,
                content="测试消息",
            )

            # 应该调用了 _run_agent
            mock_run.assert_called_once()

            # assistant 消息应使用 react_agent 模式
            assert result["assistant_message"]["content"] == "AI 回复内容"
            assert result["assistant_message"]["agent_used"] == "react_agent"


class TestAgentChatRaisesWhenUnavailable:
    """Agent 不可用时 chat() 应抛出 RuntimeError"""

    def test_chat_raises_when_unavailable(self):
        from app.agent.detection_agent import DetectionAgent

        agent = DetectionAgent()
        agent.available = False
        agent.executor = None

        import asyncio
        with pytest.raises(RuntimeError, match="不可用"):
            asyncio.get_event_loop().run_until_complete(
                agent.chat("hello")
            )
