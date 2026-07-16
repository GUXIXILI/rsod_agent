"""
对话服务单元测试
覆盖会话创建、消息发送存储、会话列表分页、会话删除（含消息级联）
"""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.entity.db_models import ChatSession, ChatMessage
from app.services.chat_service import ChatService, chat_service


class TestChatSessionCreate:
    """会话创建测试"""

    def test_create_session_default_title(self, db_session, create_test_user):
        """创建会话，默认标题"新对话\""""
        session = chat_service.create_session(db_session, create_test_user.id)
        assert session.id is not None
        assert session.title == "新对话"
        assert session.user_id == create_test_user.id
        assert session.session_uuid is not None

    def test_create_session_custom_title(self, db_session, create_test_user):
        """创建会话，自定义标题"""
        session = chat_service.create_session(db_session, create_test_user.id, title="测试对话")
        assert session.title == "测试对话"

    def test_create_multiple_sessions(self, db_session, create_test_user):
        """创建多个会话，UUID 唯一"""
        s1 = chat_service.create_session(db_session, create_test_user.id)
        s2 = chat_service.create_session(db_session, create_test_user.id)
        assert s1.session_uuid != s2.session_uuid


class TestChatSendMessage:
    """消息发送和存储测试"""

    def test_send_message_stores_both(self, db_session, create_test_user):
        """发送消息同时存储用户消息和 AI 回复"""
        session = chat_service.create_session(db_session, create_test_user.id)
        result = chat_service.send_message(
            db_session, session.id, create_test_user.id, content="你好"
        )
        assert "user_message" in result
        assert "assistant_message" in result
        assert result["user_message"]["role"] == "user"
        assert result["user_message"]["content"] == "你好"
        assert result["assistant_message"]["role"] == "assistant"

    def test_send_message_updates_session_count(self, db_session, create_test_user):
        """发送消息后会话 message_count 增加 2"""
        session = chat_service.create_session(db_session, create_test_user.id)
        chat_service.send_message(db_session, session.id, create_test_user.id, content="第一条消息")

        db_session.refresh(session)
        assert session.message_count == 2

    def test_first_message_sets_title(self, db_session, create_test_user):
        """第一条消息内容作为会话标题"""
        session = chat_service.create_session(db_session, create_test_user.id)
        chat_service.send_message(db_session, session.id, create_test_user.id, content="检测火焰")

        db_session.refresh(session)
        assert session.title == "检测火焰"

    def test_send_message_invalid_session(self, db_session, create_test_user):
        """发送到不存在的会话抛出 HTTPException"""
        with pytest.raises(HTTPException) as exc_info:
            chat_service.send_message(db_session, 9999, create_test_user.id, content="test")
        assert exc_info.value.status_code == 404


class TestChatGetSessions:
    """会话列表分页测试"""

    def test_get_sessions_empty(self, db_session, create_test_user):
        """无会话时返回空列表"""
        result = chat_service.get_sessions(db_session, create_test_user.id)
        assert result["total"] == 0
        assert result["items"] == []

    def test_get_sessions_list(self, db_session, create_test_user):
        """获取会话列表"""
        chat_service.create_session(db_session, create_test_user.id, title="会话1")
        chat_service.create_session(db_session, create_test_user.id, title="会话2")

        result = chat_service.get_sessions(db_session, create_test_user.id)
        assert result["total"] == 2

    def test_get_sessions_pagination(self, db_session, create_test_user):
        """会话列表分页"""
        for i in range(5):
            chat_service.create_session(db_session, create_test_user.id, title=f"会话{i}")

        result = chat_service.get_sessions(db_session, create_test_user.id, skip=0, limit=2)
        assert result["total"] == 5
        assert len(result["items"]) == 2
        assert result["limit"] == 2


class TestChatGetMessages:
    """获取会话消息历史测试"""

    def test_get_messages_empty(self, db_session, create_test_user):
        """新会话无消息"""
        session = chat_service.create_session(db_session, create_test_user.id)
        messages = chat_service.get_session_messages(db_session, session.id, create_test_user.id)
        assert messages == []

    def test_get_messages_after_send(self, db_session, create_test_user):
        """发送消息后能获取消息列表"""
        session = chat_service.create_session(db_session, create_test_user.id)
        chat_service.send_message(db_session, session.id, create_test_user.id, content="你好")

        messages = chat_service.get_session_messages(db_session, session.id, create_test_user.id)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"


class TestChatDeleteSession:
    """会话删除（含消息级联）测试"""

    def test_delete_session_success(self, db_session, create_test_user):
        """删除会话成功"""
        session = chat_service.create_session(db_session, create_test_user.id)
        result = chat_service.delete_session(db_session, session.id, create_test_user.id)
        assert result is True

    def test_delete_session_cascade_messages(self, db_session, create_test_user):
        """删除会话同时删除消息"""
        session = chat_service.create_session(db_session, create_test_user.id)
        chat_service.send_message(db_session, session.id, create_test_user.id, content="测试消息")

        chat_service.delete_session(db_session, session.id, create_test_user.id)

        # 消息应被级联删除
        messages = db_session.query(ChatMessage).filter(ChatMessage.session_id == session.id).all()
        assert len(messages) == 0

    def test_delete_nonexistent_session(self, db_session, create_test_user):
        """删除不存在的会话抛出 HTTPException"""
        with pytest.raises(HTTPException) as exc_info:
            chat_service.delete_session(db_session, 9999, create_test_user.id)
        assert exc_info.value.status_code == 404

    def test_cannot_delete_others_session(self, db_session, create_test_user):
        """不能删除别人的会话"""
        from app.entity.db_models import User
        from app.core.security import hash_password

        other_user = User(
            username="chat_other", email="chat_other@example.com",
            hashed_password=hash_password("Test123456"), is_active=True
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        session = chat_service.create_session(db_session, other_user.id)
        with pytest.raises(HTTPException) as exc_info:
            chat_service.delete_session(db_session, session.id, create_test_user.id)
        assert exc_info.value.status_code == 404


class TestChatServiceHelpers:
    """chat_service 静态辅助方法测试"""

    def test_extract_tool_result_summary_from_detection_json(self):
        """从检测工具 JSON 中提取 summary，避免把 base64 送入聊天正文"""
        tool_result = '{"summary": "检测到 2 个目标", "annotated_image_base64": "aGVsbG8="}'
        summary = ChatService._extract_tool_result_summary("detect_single_image", tool_result)
        assert summary == "检测到 2 个目标"
        assert "base64" not in summary

    def test_extract_tool_result_summary_fallback(self):
        """非 JSON 结果时原样返回"""
        tool_result = "plain text result"
        summary = ChatService._extract_tool_result_summary("detect_single_image", tool_result)
        assert summary == "plain text result"

    def test_has_image_file_detects_image_type(self):
        """_has_image_file 正确识别图片文件"""
        files = [{"url": "http://minio/test.jpg", "type": "image", "name": "test.jpg"}]
        assert ChatService._has_image_file(files) is True

    def test_has_image_file_defensive_data_wrapper(self):
        """_has_image_file 兼容前端未解包的 {code, data: {...}} 结构"""
        files = [{"code": 200, "data": {"url": "http://minio/test.jpg", "type": "image", "name": "test.jpg"}}]
        assert ChatService._has_image_file(files) is True

    def test_extract_first_image_url_normal(self):
        """_extract_first_image_url 正常提取图片 URL"""
        files = [
            {"url": "http://minio/video.mp4", "type": "video", "name": "video.mp4"},
            {"url": "http://minio/test.jpg", "type": "image", "name": "test.jpg"},
        ]
        assert ChatService._extract_first_image_url(files) == "http://minio/test.jpg"

    def test_extract_first_image_url_defensive_data_wrapper(self):
        """_extract_first_image_url 兼容未解包的 data 包装"""
        files = [{"code": 200, "data": {"url": "http://minio/test.jpg", "type": "image", "name": "test.jpg"}}]
        assert ChatService._extract_first_image_url(files) == "http://minio/test.jpg"


class TestChatSendMessageStream:
    """chat_service.send_message_stream 流式事件测试"""

    @staticmethod
    def _parse_sse_events(events):
        """将 SSE 原始事件流解析为 (event_type, payload) 列表"""
        parsed = []
        for raw in events:
            event_type = None
            data_line = None
            for line in raw.splitlines():
                if line.startswith("event:"):
                    event_type = line[len("event:"):].strip()
                elif line.startswith("data:"):
                    data_line = line[len("data:"):].strip()
            if event_type and data_line:
                parsed.append((event_type, json.loads(data_line)))
        return parsed

    @pytest.mark.asyncio
    async def test_send_message_stream_emits_tool_result_with_base64(self):
        """上传图片时，SSE 流应发送包含 base64 标注图的 tool_result 事件"""
        tool_result = {
            "summary": "检测到 1 个火源",
            "annotated_image_base64": "aGVsbG8=",
            "fire_object_count": 1,
            "smoke_object_count": 0,
            "detections": [
                {"class_name": "fire", "confidence": 0.9, "bbox": [0, 0, 10, 10]}
            ],
        }

        mock_session = MagicMock(spec=ChatSession)
        mock_session.id = 1
        mock_session.message_count = 0
        mock_session.last_message_at = None

        mock_db = MagicMock()
        mock_db.query.return_value = mock_db
        mock_db.filter.return_value = mock_db
        mock_db.order_by.return_value = mock_db
        mock_db.limit.return_value = mock_db
        mock_db.all.return_value = []

        with patch("app.services.chat_service.settings.LLM_STUB_MODE", True), \
             patch("app.database.session.SessionLocal", return_value=mock_db), \
             patch("app.agent.tools.detection_tool.detect_single_image") as mock_detect, \
             patch.object(chat_service, "create_session", return_value=mock_session):
            mock_detect.invoke.return_value = json.dumps(tool_result, ensure_ascii=False)

            data = SimpleNamespace(
                content="检测这张图片",
                files=[{"url": "http://minio/test.jpg", "type": "image", "name": "test.jpg"}],
            )

            events = []
            async for raw in chat_service.send_message_stream(
                user_id=1, data=data, session_id=None
            ):
                events.append(raw)

        parsed_events = self._parse_sse_events(events)

        tool_result_events = [
            payload for etype, payload in parsed_events if etype == "tool_result"
        ]
        assert len(tool_result_events) >= 1
        for payload in tool_result_events:
            result = json.loads(payload["result"])
            assert "annotated_image_base64" in result
            assert result["annotated_image_base64"] == "aGVsbG8="

        tool_end_events = [
            payload for etype, payload in parsed_events if etype == "tool_end"
        ]
        assert len(tool_end_events) >= 1
        for payload in tool_end_events:
            result = json.loads(payload["result"])
            assert "annotated_image_base64" in result

        event_types = [etype for etype, _ in parsed_events]
        assert "done" in event_types

    @pytest.mark.asyncio
    async def test_send_message_stream_handles_detection_error_json(self):
        """检测工具返回 error JSON 时，SSE 不崩溃且 error 内容被传递"""
        error_tool_result = {
            "error": "无法下载图片 'http://minio/test.jpg'，请确认 URL 是否可访问。（Connection timeout）"
        }

        mock_session = MagicMock(spec=ChatSession)
        mock_session.id = 2
        mock_session.message_count = 0
        mock_session.last_message_at = None

        mock_db = MagicMock()
        mock_db.query.return_value = mock_db
        mock_db.filter.return_value = mock_db
        mock_db.order_by.return_value = mock_db
        mock_db.limit.return_value = mock_db
        mock_db.all.return_value = []

        with patch("app.services.chat_service.settings.LLM_STUB_MODE", True), \
             patch("app.database.session.SessionLocal", return_value=mock_db), \
             patch("app.agent.tools.detection_tool.detect_single_image") as mock_detect, \
             patch.object(chat_service, "create_session", return_value=mock_session):
            mock_detect.invoke.return_value = json.dumps(error_tool_result, ensure_ascii=False)

            data = SimpleNamespace(
                content="检测这张图片",
                files=[{"url": "http://minio/test.jpg", "type": "image", "name": "test.jpg"}],
            )

            events = []
            async for raw in chat_service.send_message_stream(
                user_id=1, data=data, session_id=None
            ):
                events.append(raw)

        parsed_events = self._parse_sse_events(events)

        tool_result_events = [
            payload for etype, payload in parsed_events if etype == "tool_result"
        ]
        assert len(tool_result_events) >= 1
        for payload in tool_result_events:
            result = json.loads(payload["result"])
            assert "error" in result
            assert "无法下载图片" in result["error"]

        tool_end_events = [
            payload for etype, payload in parsed_events if etype == "tool_end"
        ]
        assert len(tool_end_events) >= 1
        for payload in tool_end_events:
            result = json.loads(payload["result"])
            assert "error" in result

        event_types = [etype for etype, _ in parsed_events]
        assert "done" in event_types
        assert "error" not in event_types
