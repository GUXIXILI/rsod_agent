"""
Chat 服务 LLM 集成测试
覆盖 _call_llm 正常/异常返回、元组格式验证、send_message 写入、历史上下文、SSE 流式生成器
使用 pytest + unittest.mock，Mock ChatOpenAI 避免真实 API 调用
"""
import json
import time
from unittest.mock import MagicMock, patch

import pytest

from app.services.chat_service import ChatService, chat_service
from app.entity.db_models import ChatSession, ChatMessage


@pytest.fixture(autouse=True)
def _ensure_llm_settings():
    """确保 settings 模块有 LLM 相关属性（ChatOpenAI 构造时需要）"""
    from app.config import settings as _settings_mod

    attrs = {
        "QWEN_MODEL": "qwen-plus",
        "QWEN_API_KEY": "test-key",
        "QWEN_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    }
    missing = {}
    for key, val in attrs.items():
        if not hasattr(_settings_mod, key):
            setattr(_settings_mod, key, val)
            missing[key] = val
    yield
    for key in missing:
        try:
            delattr(_settings_mod, key)
        except AttributeError:
            pass


class TestCallLLMNormal:
    """_call_llm 正常返回测试"""

    @patch("app.services.chat_service.ChatOpenAI")
    def test_call_llm_returns_content(self, mock_chat_openai_cls):
        """Mock ChatOpenAI.invoke() 返回含 content 的对象"""
        mock_response = MagicMock()
        mock_response.content = "这是 AI 的测试回复"
        mock_response.usage_metadata = {"total_tokens": 42}

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_chat_openai_cls.return_value = mock_llm

        svc = ChatService()
        content, tokens_used, latency_ms = svc._call_llm("你好")

        assert content == "这是 AI 的测试回复"
        assert tokens_used == 42
        assert latency_ms >= 0

    @patch("app.services.chat_service.ChatOpenAI")
    def test_call_llm_returns_tuple_format(self, mock_chat_openai_cls):
        """验证 _call_llm 返回 (content, tokens_used, latency_ms) 三元组"""
        mock_response = MagicMock()
        mock_response.content = "回复内容"
        mock_response.usage_metadata = {"total_tokens": 100}

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_chat_openai_cls.return_value = mock_llm

        svc = ChatService()
        result = svc._call_llm("测试消息")

        assert isinstance(result, tuple)
        assert len(result) == 3
        content, tokens_used, latency_ms = result
        assert isinstance(content, str)
        assert isinstance(tokens_used, int)
        assert isinstance(latency_ms, int)

    @patch("app.services.chat_service.ChatOpenAI")
    def test_call_llm_no_usage_metadata(self, mock_chat_openai_cls):
        """当 response 没有 usage_metadata 时 tokens_used 为 0"""
        mock_response = MagicMock()
        mock_response.content = "无 token 信息的回复"
        mock_response.usage_metadata = None

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_chat_openai_cls.return_value = mock_llm

        svc = ChatService()
        content, tokens_used, latency_ms = svc._call_llm("测试")

        assert content == "无 token 信息的回复"
        assert tokens_used == 0

    @patch("app.services.chat_service.ChatOpenAI")
    def test_call_llm_usage_metadata_missing_total_tokens(self, mock_chat_openai_cls):
        """usage_metadata 存在但缺少 total_tokens 键"""
        mock_response = MagicMock()
        mock_response.content = "回复"
        mock_response.usage_metadata = {"input_tokens": 10}

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_chat_openai_cls.return_value = mock_llm

        svc = ChatService()
        content, tokens_used, latency_ms = svc._call_llm("测试")

        assert tokens_used == 0


class TestCallLLMException:
    """_call_llm 异常处理测试"""

    @patch("app.services.chat_service.ChatOpenAI")
    def test_call_llm_exception_returns_friendly_error(self, mock_chat_openai_cls):
        """Mock 抛出异常时返回友好错误信息"""
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("API rate limit exceeded")
        mock_chat_openai_cls.return_value = mock_llm

        svc = ChatService()
        content, tokens_used, latency_ms = svc._call_llm("你好")

        assert "AI 服务暂时不可用" in content
        assert "请稍后重试" in content
        assert tokens_used == 0
        assert latency_ms == 0

    @patch("app.services.chat_service.ChatOpenAI")
    def test_call_llm_constructor_exception(self, mock_chat_openai_cls):
        """ChatOpenAI 构造时抛异常（如无效 API Key）"""
        mock_chat_openai_cls.side_effect = ValueError("Invalid API key")

        svc = ChatService()
        content, tokens_used, latency_ms = svc._call_llm("你好")

        assert "AI 服务暂时不可用" in content
        assert tokens_used == 0


class TestCallLLMWithHistory:
    """_call_llm 历史上下文测试"""

    @patch("app.services.chat_service.ChatOpenAI")
    def test_call_llm_with_history(self, mock_chat_openai_cls):
        """验证 history 参数正确传递给 LLM"""
        mock_response = MagicMock()
        mock_response.content = "带上下文的回复"
        mock_response.usage_metadata = {"total_tokens": 50}

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_chat_openai_cls.return_value = mock_llm

        svc = ChatService()
        history = [
            {"role": "user", "content": "之前的问题"},
            {"role": "assistant", "content": "之前的回复"},
        ]
        content, tokens_used, latency_ms = svc._call_llm("新问题", history=history)

        assert content == "带上下文的回复"
        # 验证 invoke 被调用，且 messages 包含 system + 2 history + 1 current = 4 条
        call_args = mock_llm.invoke.call_args
        messages = call_args[0][0]
        assert len(messages) == 4

    @patch("app.services.chat_service.ChatOpenAI")
    def test_call_llm_history_truncated_to_10(self, mock_chat_openai_cls):
        """历史消息最多取最近 10 条"""
        mock_response = MagicMock()
        mock_response.content = "回复"
        mock_response.usage_metadata = {"total_tokens": 20}

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_chat_openai_cls.return_value = mock_llm

        svc = ChatService()
        history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"消息{i}"} for i in range(15)]
        svc._call_llm("新消息", history=history)

        call_args = mock_llm.invoke.call_args
        messages = call_args[0][0]
        # system(1) + history[-10:](10) + current(1) = 12
        assert len(messages) == 12


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

        with patch("app.services.chat_service.ChatOpenAI") as mock_cls, \
             patch("app.database.session.SessionLocal") as mock_session_local:
            mock_session_local.return_value = db_session
            mock_llm = MagicMock()

            async def fake_astream(messages):
                mock_chunk1 = MagicMock()
                mock_chunk1.content = "你好"
                mock_chunk1.usage_metadata = None
                yield mock_chunk1
                mock_chunk2 = MagicMock()
                mock_chunk2.content = "世界"
                mock_chunk2.usage_metadata = None
                yield mock_chunk2

            mock_llm.astream = fake_astream
            mock_cls.return_value = mock_llm

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

        with patch("app.services.chat_service.ChatOpenAI") as mock_cls, \
             patch("app.database.session.SessionLocal") as mock_session_local:
            mock_session_local.return_value = db_session
            mock_llm = MagicMock()

            async def fake_astream(messages):
                mock_chunk = MagicMock()
                mock_chunk.content = "回复"
                mock_chunk.usage_metadata = None
                yield mock_chunk

            mock_llm.astream = fake_astream
            mock_cls.return_value = mock_llm

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
