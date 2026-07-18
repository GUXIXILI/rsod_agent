"""
SSE 流式接口 error 事件测试
验证 error 事件 payload 包含非空 content 字段
"""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.agent.detection_agent import detection_agent
from app.services.chat_service import ChatService, chat_service


class _FakeQuery:
    def filter(self, *args, **kwargs):
        return self

    def filter_by(self, **kwargs):
        return self

    def order_by(self, *args):
        return self

    def limit(self, n):
        return self

    def all(self):
        return []

    def first(self):
        return None

    def count(self):
        return 0


class _FakeSession:
    """不依赖真实数据库的最小 Session 替身"""

    def __init__(self):
        self._next_id = 1

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = self._next_id
            self._next_id += 1

    def commit(self):
        pass

    def refresh(self, obj):
        pass

    def rollback(self):
        pass

    def close(self):
        pass

    def query(self, model):
        return _FakeQuery()


def _parse_sse_event(event: str):
    lines = event.strip().splitlines()
    data_line = next((line for line in lines if line.startswith("data: ")), None)
    if data_line is None:
        return None
    return json.loads(data_line[len("data: "):])


class TestSendMessageStreamError:
    """send_message_stream error 事件测试"""

    @pytest.fixture
    def service(self):
        return ChatService()

    @pytest.fixture(autouse=True)
    def patch_session_local(self):
        """用不访问真实数据库的 Session 替换 SessionLocal"""
        with patch("app.database.session.SessionLocal", _FakeSession):
            yield

    def test_detection_agent_unavailable_yields_error_with_content(self, service):
        """DetectionAgent 不可用时，SSE 会返回带非空 content 的 error 事件"""
        data = SimpleNamespace(content="检测这张图片", files=None)

        with patch.object(detection_agent, "available", False):
            with patch("app.services.chat_service.settings.LLM_STUB_MODE", False):
                events = []
                async def _collect():
                    async for event in service.send_message_stream(user_id=1, data=data):
                        events.append(event)
                asyncio.run(_collect())

        error_events = [e for e in events if e.startswith("event: error")]
        assert len(error_events) >= 1

        for event in error_events:
            payload = _parse_sse_event(event)
            assert payload is not None
            assert payload.get("content")
            assert len(payload["content"].strip()) > 0

    def test_outer_catch_error_includes_exception_detail(self, service):
        """最外层异常捕获返回的 error 事件应包含具体异常信息"""
        data = SimpleNamespace(content="hello", files=None)

        events = []
        async def _collect():
            async for event in service.send_message_stream(user_id=1, data=data, session_id=9999):
                events.append(event)
        asyncio.run(_collect())

        error_events = [e for e in events if e.startswith("event: error")]
        assert len(error_events) >= 1

        payload = _parse_sse_event(error_events[0])
        assert payload is not None
        assert "会话不存在或无权访问" in payload["content"]
