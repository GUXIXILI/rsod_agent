"""
视频异步检测功能测试

测试 VideoTaskService 和视频异步 API：
- submit_video_task 应返回 task_id
- 查询不存在的 task 应返回默认进度
- 进度字典应正确更新
- Redis 优先于数据库查询进度
- 进度更新同步写入 Redis
"""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


class TestSubmitVideoTask:
    """提交视频异步任务应返回 task"""

    @patch("app.services.video_task_service.detection_service")
    def test_submit_video_task(self, mock_detection, db_session, create_test_user):
        from app.services.video_task_service import VideoTaskService

        svc = VideoTaskService()

        # 不调用实际检测
        task = svc.submit_video_task(
            db=db_session,
            user_id=create_test_user.id,
            scene_id=1,
            video_bytes=b"\x00\x00\x00\x1cftypisom",
            filename="test.mp4",
        )
        assert task.id is not None
        assert task.status == "processing"
        assert task.task_type == "video"

        # 内存进度应已初始化（后台线程可能已更新为 10）
        progress = svc.get_task_progress(task.id)
        assert progress["progress"] >= 0


class TestGetProgressUnknown:
    """查询不存在的 task 应返回默认进度"""

    def test_get_progress_unknown(self, db_session):
        from app.services.video_task_service import VideoTaskService

        svc = VideoTaskService()

        # 不存在的 task_id，内存和 DB 都找不到
        progress = svc.get_task_progress(99999, db_session)
        assert progress["task_id"] == 99999
        assert progress["progress"] == 0


class TestProgressTracking:
    """进度字典应正确更新"""

    def test_progress_tracking(self, db_session, create_test_user, monkeypatch):
        from app.services.video_task_service import VideoTaskService

        svc = VideoTaskService()
        monkeypatch.setattr(svc, "_get_redis_client", lambda: None)

        # 模拟手动更新进度
        svc._progress[42] = 0
        assert svc.get_task_progress(42)["progress"] == 0

        svc._update_progress(42, 50)
        assert svc.get_task_progress(42)["progress"] == 50

        svc._update_progress(42, 100)
        assert svc.get_task_progress(42)["progress"] == 100

    def test_redis_progress_has_priority_over_database(self, monkeypatch):
        from app.services.video_task_service import VideoTaskService

        class FakeRedis:
            def get(self, key):
                assert key == "video:progress:42"
                return json.dumps({"progress": 64, "current_frame": 64, "total_frames": 100})

        svc = VideoTaskService()
        monkeypatch.setattr(svc, "_get_redis_client", lambda: FakeRedis())
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
            progress=10, status="processing"
        )

        progress = svc.get_task_progress(42, db)

        assert progress == {
            "task_id": 42,
            "progress": 64,
            "current_frame": 64,
            "total_frames": 100,
            "status": "processing",
        }

    def test_database_progress_is_used_when_redis_is_unavailable(self, monkeypatch):
        from app.services.video_task_service import VideoTaskService

        svc = VideoTaskService()
        monkeypatch.setattr(svc, "_get_redis_client", lambda: None)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
            progress=55, status="processing"
        )

        progress = svc.get_task_progress(42, db)

        assert progress == {"task_id": 42, "progress": 55, "status": "processing"}

    def test_progress_update_writes_to_redis(self, monkeypatch):
        from app.services.video_task_service import VideoTaskService

        class FakeRedis:
            def __init__(self):
                self.values = {}

            def set(self, key, value, ex):
                self.values[key] = (value, ex)

        fake_redis = FakeRedis()
        svc = VideoTaskService()
        monkeypatch.setattr(svc, "_get_redis_client", lambda: fake_redis)

        svc._update_progress(42, 63)

        value, ttl = fake_redis.values["video:progress:42"]
        assert json.loads(value) == {"progress": 63}
        assert ttl == svc._PROGRESS_TTL_SECONDS


class TestVideoAsyncAPI:
    """视频异步 API 端点测试"""

    def test_submit_requires_auth(self, client, db_session):
        """未认证时应拒绝请求"""
        response = client.post(
            "/api/detection/video/async",
            data={"scene_id": "1"},
            files={"file": ("test.mp4", b"\x00" * 10, "video/mp4")},
        )
        assert response.status_code == 401

    def test_get_status_requires_auth(self, client, db_session):
        """查询进度未认证时应拒绝"""
        response = client.get("/api/detection/video/status/1")
        assert response.status_code == 401
