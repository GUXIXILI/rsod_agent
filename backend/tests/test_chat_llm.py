"""
Chat 服务本地占位实现测试
覆盖占位回复、消息写入、历史上下文和 SSE 流式生成器，确保不会调用外部大模型 API。
"""
import json
from unittest.mock import MagicMock, patch

from app.config.settings import settings
from app.services.chat_service import ChatService, chat_service
from app.entity.db_models import ChatSession, ChatMessage


class TestCallLLMStub:
    """本地占位回复测试。"""

    def test_call_llm_returns_tuple_format(self):
        """占位实现仍返回内容、估算 token 数和延迟三元组。"""
        result = ChatService()._call_llm("测试消息")

        assert isinstance(result, tuple)
        assert len(result) == 3
        content, tokens_used, latency_ms = result
        assert "本地占位回复" in content
        assert "未连接真实大模型服务" in content
        assert tokens_used > 0
        assert latency_ms >= 0

    def test_call_llm_returns_fire_specific_reply(self):
        """火灾烟雾关键词返回安全提示。"""
        content, _, _ = ChatService()._call_llm("检测到烟雾应该怎么办")

        assert "火灾烟雾检测相关问题" in content
        assert "人工复核" in content

    def test_call_llm_history_is_reflected_without_external_request(self):
        """存在历史上下文时，占位回复明确说明已读取上下文。"""
        history = [{"role": "user", "content": "之前的问题"}]
        content, _, _ = ChatService()._call_llm("继续", history=history)

        assert "会话上下文" in content

    def test_call_llm_is_deterministic(self):
        """相同输入应得到完全一致的本地回复。"""
        first = ChatService()._call_llm("普通问题")[0]
        second = ChatService()._call_llm("普通问题")[0]

        assert first == second

    def test_stub_mode_is_enabled_by_default(self):
        """默认配置必须启用本地占位模式。"""
        assert settings.LLM_STUB_MODE is True

    def test_call_llm_accepts_empty_content(self):
        """空内容仍返回合法占位回复，不触发外部请求。"""
        content, tokens_used, latency_ms = ChatService()._call_llm("")

        assert "本地占位回复" in content
        assert tokens_used > 0
        assert latency_ms >= 0

    def test_call_llm_truncates_echoed_content(self):
        """普通消息只回显前 50 个字符，避免占位回复无限增长。"""
        content, _, _ = ChatService()._call_llm("A" * 60)

        assert "A" * 50 in content
        assert "A" * 51 not in content

    def test_call_llm_token_estimate_is_stable(self):
        """相同输入的 token 估算值保持稳定。"""
        first = ChatService()._call_llm("稳定性测试")[1]
        second = ChatService()._call_llm("稳定性测试")[1]

        assert first == second
        assert isinstance(first, int)


class TestSendMessageWithLLM:
    """send_message 中 LLM 集成测试"""

    @patch.object(ChatService, "_call_llm")
    def test_send_message_stores_tokens_and_latency(self, mock_call_llm, db_session, create_test_user):
        """mock _call_llm，验证 DB 写入 tokens_used 和 latency_ms"""
        mock_call_llm.return_value = ("AI 回复内容", 128, 350)

        session = chat_service.create_session(db_session, create_test_user.id)
        result = chat_service.send_message(
            db_session, session.id, create_test_user.id, content="测试 Token 记录"
        )

        assert result["assistant_message"]["content"] == "AI 回复内容"
        assert result["assistant_message"]["agent_used"] == "supervisor"

        # 验证 DB 中的 assistant 消息
        msgs = db_session.query(ChatMessage).filter(
            ChatMessage.session_id == session.id,
            ChatMessage.role == "assistant"
        ).all()
        assert len(msgs) == 1
        assert msgs[0].tokens_used == 128
        assert msgs[0].latency_ms == 350

    @patch.object(ChatService, "_call_llm")
    def test_send_message_zero_tokens_stored_as_none(self, mock_call_llm, db_session, create_test_user):
        """tokens_used=0 时 DB 存储为 None"""
        mock_call_llm.return_value = ("AI 回复", 0, 0)

        session = chat_service.create_session(db_session, create_test_user.id)
        chat_service.send_message(db_session, session.id, create_test_user.id, content="测试零 token")

        msgs = db_session.query(ChatMessage).filter(
            ChatMessage.session_id == session.id,
            ChatMessage.role == "assistant"
        ).all()
        assert len(msgs) == 1
        assert msgs[0].tokens_used is None
        assert msgs[0].latency_ms is None

    @patch.object(ChatService, "_call_llm")
    def test_send_message_passes_history(self, mock_call_llm, db_session, create_test_user):
        """验证 send_message 传递历史上下文给 _call_llm"""
        mock_call_llm.return_value = ("回复", 10, 100)

        session = chat_service.create_session(db_session, create_test_user.id)

        # 先发一条消息，产生历史
        chat_service.send_message(db_session, session.id, create_test_user.id, content="第一条消息")

        # 第二次发消息时 _call_llm 应该接收到历史
        mock_call_llm.return_value = ("第二条回复", 15, 120)
        chat_service.send_message(db_session, session.id, create_test_user.id, content="第二条消息")

        # 第二次调用时 history 应包含之前的消息
        call_args = mock_call_llm.call_args
        # _call_llm(content, history=history) — history 通过 keyword 传入
        history = call_args.kwargs.get("history")
        assert history is not None
        assert len(history) > 0


class TestSendMessageStream:
    """send_message_stream SSE 流式生成器测试"""

    async def test_stream_yields_start_event(self, db_session, create_test_user):
        """验证流式生成器 yield start 事件"""
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

        assert "start" in event_types
        assert "token" in event_types
        assert "done" in event_types

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

        start_event = next(e for e in events if e.startswith("event: start"))
        data_line = start_event.split("data: ")[1].strip()
        start_data = json.loads(data_line)
        assert start_data["session_id"] is not None
        assert start_data["session_id"] > 0
