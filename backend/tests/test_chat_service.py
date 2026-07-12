"""
对话服务单元测试
覆盖会话创建、消息发送存储、会话列表分页、会话删除（含消息级联）
"""
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
