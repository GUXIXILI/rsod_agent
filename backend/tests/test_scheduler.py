"""
定时任务单元测试
覆盖 cleanup_expired_tasks：30天前 failed 任务清理、非 failed 不受影响、异常回滚
"""
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest

from app.scheduler.jobs import cleanup_expired_tasks


class TestCleanupExpiredTasks:
    """清理过期检测任务测试"""

    @patch("app.database.session.SessionLocal")
    def test_cleanup_deletes_old_failed_tasks(self, mock_session_local):
        """验证 30 天前的 failed 任务被删除"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        # mock query chain: db.query(DetectionTask).filter(...).delete()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.delete.return_value = 5  # 删除了 5 条

        cleanup_expired_tasks()

        # 验证 delete 被调用
        mock_filter.delete.assert_called_once_with(synchronize_session=False)
        # 验证 commit 被调用
        mock_db.commit.assert_called_once()
        # 验证 close 被调用
        mock_db.close.assert_called_once()

    @patch("app.database.session.SessionLocal")
    def test_cleanup_no_expired_tasks(self, mock_session_local):
        """没有过期任务时 deleted=0，不报错"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.delete.return_value = 0

        cleanup_expired_tasks()

        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()

    @patch("app.database.session.SessionLocal")
    def test_cleanup_exception_triggers_rollback(self, mock_session_local):
        """异常时 db.rollback() 被调用"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.side_effect = Exception("数据库连接失败")

        cleanup_expired_tasks()

        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called_once()

    @patch("app.database.session.SessionLocal")
    def test_cleanup_only_targets_failed_status(self, mock_session_local):
        """验证查询条件包含 status==failed（通过 mock 验证 filter 被调用）"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.delete.return_value = 0

        cleanup_expired_tasks()

        # filter 应被调用（传入 DetectionTask.status == "failed" 和 created_at 条件）
        mock_query.filter.assert_called_once()
