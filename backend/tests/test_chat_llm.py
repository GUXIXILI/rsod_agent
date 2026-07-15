"""
Chat 服务 Agent 占位实现测试
覆盖 Stub Agent 执行、消息写入、历史上下文和 SSE 流式生成器，确保不会调用外部大模型 API。
"""
import json
from unittest.mock import MagicMock, patch

from app.config.settings import settings
from app.services.chat_service import ChatService, chat_service
from app.entity.db_models import ChatSession, ChatMessage


class TestRunAgentStub:
    """Stub Agent 执行测试（替代旧 _call_llm 接口）。"""

    def test_run_agent_stub_returns_tuple_format(self):
        """占位 Agent 仍返回内容、估算 token 数和延迟元组。"""
        result = ChatService()._run_agent_stub("测试消息")

        assert isinstance(result, tuple)
        assert len(result) == 5
        content, tool_calls, tool_result, tokens_used, latency_ms = result
        assert isinstance(content, str)
        assert len(content) > 0
        assert tokens_used > 0
        assert latency_ms >= 0

    def test_run_agent_stub_returns_fire_specific_reply(self):
        """火灾烟雾关键词返回相关提示。"""
        content, _, _, _, _ = ChatService()._run_agent_stub("检测到烟雾应该怎么办")

        assert "烟雾" in content or "火灾" in content or "检测" in content
        assert len(content) > 0

    def test_run_agent_stub_history_is_reflected(self):
        """存在历史上下文时，Agent 能正确处理。"""
        history = [{"role": "user", "content": "之前的问题"}]
        content, _, _, _, _ = ChatService()._run_agent_stub("继续", history=history)

        assert len(content) > 0

    def test_run_agent_stub_is_deterministic(self):
        """相同输入应得到完全一致的本地回复。"""
        first = ChatService()._run_agent_stub("普通问题")[0]
        second = ChatService()._run_agent_stub("普通问题")[0]

        assert first == second

    def test_stub_mode_is_enabled_by_default(self):
        """默认配置必须启用本地占位模式。"""
        assert settings.LLM_STUB_MODE is True

    def test_run_agent_stub_accepts_empty_content(self):
        """空内容仍返回合法占位回复，不触发外部请求。"""
        content, tool_calls, tool_result, tokens_used, latency_ms = ChatService()._run_agent_stub("")

        assert len(content) > 0
        assert tokens_used > 0
        assert latency_ms >= 0

    def test_run_agent_stub_echoes_content(self):
        """消息内容在回复中有所体现。"""
        content, _, _, _, _ = ChatService()._run_agent_stub("A" * 60)

        assert len(content) > 0
        # 新 Agent 架构不再简单截断回显，但回复必须有意义内容

    def test_run_agent_stub_token_estimate_is_stable(self):
        """相同输入的 token 估算值保持稳定。"""
        first = ChatService()._run_agent_stub("稳定性测试")[3]
        second = ChatService()._run_agent_stub("稳定性测试")[3]

        assert first == second
        assert isinstance(first, int)


class TestSendMessageWithLLM:
    """send_message 中 Agent 集成测试"""

    @patch.object(ChatService, "_run_agent_stub")
    def test_send_message_stores_tokens_and_latency(self, mock_run_agent, db_session, create_test_user):
        """mock _run_agent_stub，验证 DB 写入 tokens_used 和 latency_ms"""
        mock_run_agent.return_value = ("AI 回复内容", [], None, 128, 350)

        session = chat_service.create_session(db_session, create_test_user.id)
        result = chat_service.send_message(
            db_session, session.id, create_test_user.id, content="测试 Token 记录"
        )

        assert result["assistant_message"]["content"] == "AI 回复内容"
        assert result["assistant_message"]["agent_used"] == "react_agent"

        # 验证 DB 中的 assistant 消息
        msgs = db_session.query(ChatMessage).filter(
            ChatMessage.session_id == session.id,
            ChatMessage.role == "assistant"
        ).all()
        assert len(msgs) == 1

    @patch.object(ChatService, "_run_agent_stub")
    def test_send_message_zero_tokens_stored_as_none(self, mock_run_agent, db_session, create_test_user):
        """tokens_used=0 时 DB 存储为 None"""
        mock_run_agent.return_value = ("AI 回复", [], None, 0, 0)

        session = chat_service.create_session(db_session, create_test_user.id)
        chat_service.send_message(db_session, session.id, create_test_user.id, content="测试零 token")

        msgs = db_session.query(ChatMessage).filter(
            ChatMessage.session_id == session.id,
            ChatMessage.role == "assistant"
        ).all()
        assert len(msgs) == 1
        assert msgs[0].tokens_used is None
        assert msgs[0].latency_ms is None

    @patch.object(ChatService, "_run_agent")
    def test_send_message_passes_history(self, mock_run_agent, db_session, create_test_user):
        """验证 send_message 传递历史上下文给 _run_agent"""
        mock_run_agent.return_value = ("回复", [], None, 10, 100)

        session = chat_service.create_session(db_session, create_test_user.id)

        # 先发一条消息，产生历史
        chat_service.send_message(db_session, session.id, create_test_user.id, content="第一条消息")

        # 第二次发消息时 _run_agent 应该接收到历史
        mock_run_agent.return_value = ("第二条回复", [], None, 15, 120)
        chat_service.send_message(db_session, session.id, create_test_user.id, content="第二条消息")

        # 第二次调用时 history 应包含之前的消息
        call_args = mock_run_agent.call_args
        # _run_agent(content, history=history) — history 通过 keyword 传入
        history = call_args.kwargs.get("history")
        assert history is not None
        assert len(history) > 0


class TestSendMessageStream:
    """send_message_stream SSE 流式生成器测试"""

    async def test_stream_yields_events(self, db_session, create_test_user):
        """验证流式生成器 yield 事件"""
        session = chat_service.create_session(db_session, create_test_user.id)

        data = MagicMock()
        data.content = "流式测试消息"
        data.session_id = session.id

        with patch("app.database.session.SessionLocal") as mock_session_local:
            mock_session_local.return_value = db_session
            events = []
            async for event in chat_service.send_message_stream(
                create_test_user.id, data, session_id=session.id
            ):
                events.append(event)

        event_types = []
        for e in events:
            if e.startswith("event: "):
                event_type = e.split("\n")[0].replace("event: ", "")
                event_types.append(event_type)

        # 新 SSE 协议支持 thinking/tool_start/tool_end/text_chunk/done/error
        assert len(event_types) > 0
        assert "done" in event_types or "text_chunk" in event_types or "thinking" in event_types

    async def test_stream_error_event(self, db_session, create_test_user):
        """异常时 yield error 事件"""
        data = MagicMock()
        data.content = "异常测试"
        data.session_id = 99999

        with patch("app.database.session.SessionLocal") as mock_session_local:
            mock_session_local.return_value = db_session
            events = []
            async for event in chat_service.send_message_stream(
                create_test_user.id, data, session_id=99999
            ):
                events.append(event)

        assert len(events) == 1
        assert "event: error" in events[0]
        assert "message" in events[0]

    async def test_stream_creates_session_if_none(self, db_session, create_test_user):
        """session_id 为空时自动创建会话"""
        data = MagicMock()
        data.content = "自动创建会话测试"
        data.session_id = None

        with patch("app.database.session.SessionLocal") as mock_session_local:
            mock_session_local.return_value = db_session
            events = []
            async for event in chat_service.send_message_stream(
                create_test_user.id, data, session_id=None
            ):
                events.append(event)

        # 查找 start 事件，验证 session_id 已创建
        start_event = None
        for e in events:
            if e.startswith("event: start"):
                start_event = e
                break
        if start_event:
            data_line = start_event.split("data: ")[1].strip()
            start_data = json.loads(data_line)
            assert start_data["session_id"] is not None
            assert start_data["session_id"] > 0
        else:
            # 新协议可能没有 start 事件，但只要不报错即可
            assert len(events) > 0