"""
审计日志单元测试
覆盖 OperationLog 创建时 request_body 字段正确设置
"""
from unittest.mock import patch, MagicMock

import pytest

from app.middleware.audit_log import AuditLogMiddleware


class TestAuditLogRequestBody:
    """验证 OperationLog 创建时 request_body 字段被正确设置"""

    @patch("app.database.session.SessionLocal")
    def test_save_log_sets_request_body(self, mock_session_local):
        """_save_log 写入 request_body 字段"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        middleware = AuditLogMiddleware.__new__(AuditLogMiddleware)
        middleware._save_log(
            user_id=1,
            username="testuser",
            module="detection",
            action="create",
            target_type="task",
            target_id="42",
            description="POST /api/detection",
            ip_address="127.0.0.1",
            user_agent="pytest",
            request_method="POST",
            request_path="/api/detection",
            status="success",
            body_summary='{"scene_id": 1, "file_name": "test.jpg"}',
        )

        # 验证 db.add 被调用，且传入的 OperationLog 对象包含 request_body
        mock_db.add.assert_called_once()
        log_obj = mock_db.add.call_args[0][0]
        assert log_obj.request_body == '{"scene_id": 1, "file_name": "test.jpg"}'
        mock_db.commit.assert_called_once()

    @patch("app.database.session.SessionLocal")
    def test_save_log_request_body_none_when_empty(self, mock_session_local):
        """body_summary 为空时 request_body 为 None"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        middleware = AuditLogMiddleware.__new__(AuditLogMiddleware)
        middleware._save_log(
            user_id=1,
            username="testuser",
            module="auth",
            action="create",
            target_type="token",
            target_id=None,
            description="POST /api/auth/login",
            ip_address="127.0.0.1",
            user_agent="pytest",
            request_method="POST",
            request_path="/api/auth/login",
            status="success",
            body_summary=None,
        )

        mock_db.add.assert_called_once()
        log_obj = mock_db.add.call_args[0][0]
        assert log_obj.request_body is None

    @patch("app.database.session.SessionLocal")
    def test_save_log_request_body_with_sensitive_data(self, mock_session_local):
        """request_body 包含脱敏后的密码字段"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        middleware = AuditLogMiddleware.__new__(AuditLogMiddleware)
        middleware._save_log(
            user_id=None,
            username=None,
            module="auth",
            action="create",
            target_type="user",
            target_id=None,
            description="POST /api/auth/register",
            ip_address="192.168.1.100",
            user_agent="pytest",
            request_method="POST",
            request_path="/api/auth/register",
            status="success",
            body_summary='{"username": "newuser", "password": "***"}',
        )

        mock_db.add.assert_called_once()
        log_obj = mock_db.add.call_args[0][0]
        assert "***" in log_obj.request_body
        assert "newuser" in log_obj.request_body

    @patch("app.database.session.SessionLocal")
    def test_save_log_db_error_triggers_rollback(self, mock_session_local):
        """数据库写入失败时触发 rollback"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.add.side_effect = Exception("DB connection error")

        middleware = AuditLogMiddleware.__new__(AuditLogMiddleware)
        # _save_log 内部捕获异常，不应抛出
        middleware._save_log(
            user_id=1,
            module="system",
            action="update",
            description="test",
            body_summary="test body",
        )

        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called_once()
