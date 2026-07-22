"""
历史记录服务单元测试
覆盖分页查询、筛选条件、用户隔离、任务详情、删除功能
"""
from datetime import datetime, timedelta

import pytest

from app.entity.db_models import DetectionScene, DetectionTask, DetectionResult
from app.services.history_service import HistoryService, history_service


def _create_scene(db_session, name="scene_hist"):
    scene = DetectionScene(
        name=name, display_name="测试场景", category="fire",
        class_names=["fire", "smoke"]
    )
    db_session.add(scene)
    db_session.commit()
    db_session.refresh(scene)
    return scene


def _create_task(db_session, user_id, scene_id, fire_level="safe", file_name="img.jpg", created_at=None):
    task = DetectionTask(
        user_id=user_id,
        scene_id=scene_id,
        task_type="single",
        file_name=file_name,
        status="completed",
        fire_level=fire_level,
        fire_object_count=1 if fire_level in ("warning", "danger") else 0,
        smoke_object_count=0,
        detected_at=created_at or datetime.now(),
        created_at=created_at or datetime.now(),
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


class TestHistoryPagination:
    """分页查询测试"""

    def test_default_pagination(self, db_session, create_test_user):
        """默认 page=1, page_size=20"""
        scene = _create_scene(db_session)
        for i in range(5):
            _create_task(db_session, create_test_user.id, scene.id, file_name=f"img_{i}.jpg")

        result = history_service.get_tasks(db_session, create_test_user.id)
        assert result["total"] == 5
        assert result["page"] == 1
        assert result["page_size"] == 20
        assert len(result["items"]) == 5

    def test_custom_page_size(self, db_session, create_test_user):
        """自定义 page_size 限制返回数量"""
        scene = _create_scene(db_session, name="scene_page")
        for i in range(10):
            _create_task(db_session, create_test_user.id, scene.id, file_name=f"file_{i}.jpg")

        result = history_service.get_tasks(db_session, create_test_user.id, page=1, page_size=3)
        assert result["total"] == 10
        assert len(result["items"]) == 3
        assert result["page_size"] == 3

    def test_second_page(self, db_session, create_test_user):
        """查询第二页"""
        scene = _create_scene(db_session, name="scene_page2")
        for i in range(5):
            _create_task(db_session, create_test_user.id, scene.id, file_name=f"f_{i}.jpg")

        result = history_service.get_tasks(db_session, create_test_user.id, page=2, page_size=2)
        assert len(result["items"]) == 2

    def test_empty_result(self, db_session, create_test_user):
        """无记录时返回空列表"""
        result = history_service.get_tasks(db_session, create_test_user.id)
        assert result["total"] == 0
        assert result["items"] == []


class TestHistoryFilters:
    """筛选条件测试"""

    def test_filter_by_fire_level(self, db_session, create_test_user):
        """按火情等级筛选"""
        scene = _create_scene(db_session, name="scene_fl")
        _create_task(db_session, create_test_user.id, scene.id, fire_level="danger", file_name="d.jpg")
        _create_task(db_session, create_test_user.id, scene.id, fire_level="safe", file_name="s.jpg")

        result = history_service.get_tasks(db_session, create_test_user.id, fire_level="danger")
        assert result["total"] == 1
        assert result["items"][0]["fire_level"] == "danger"

    def test_filter_by_file_name(self, db_session, create_test_user):
        """按文件名模糊搜索"""
        scene = _create_scene(db_session, name="scene_fn")
        _create_task(db_session, create_test_user.id, scene.id, file_name="fire_photo.jpg")
        _create_task(db_session, create_test_user.id, scene.id, file_name="smoke_photo.jpg")

        result = history_service.get_tasks(db_session, create_test_user.id, file_name="fire")
        assert result["total"] == 1
        assert "fire" in result["items"][0]["file_name"]

    def test_filter_by_time_range(self, db_session, create_test_user):
        """按时间范围筛选"""
        scene = _create_scene(db_session, name="scene_tr")
        now = datetime.now()
        _create_task(db_session, create_test_user.id, scene.id, file_name="old.jpg",
                     created_at=now - timedelta(days=30))
        _create_task(db_session, create_test_user.id, scene.id, file_name="new.jpg",
                     created_at=now)

        result = history_service.get_tasks(
            db_session, create_test_user.id,
            start_time=now - timedelta(days=7),
            end_time=now + timedelta(days=1),
        )
        assert result["total"] == 1
        assert result["items"][0]["file_name"] == "new.jpg"


class TestHistoryUserIsolation:
    """用户隔离测试"""

    def test_user_cannot_see_others_tasks(self, db_session, create_test_user):
        """用户只能看到自己的任务"""
        from app.entity.db_models import User
        from app.core.security import hash_password

        scene = _create_scene(db_session, name="scene_iso")
        other_user = User(
            username="other_user", email="other@example.com",
            hashed_password=hash_password("Test123456"), is_active=True
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        _create_task(db_session, create_test_user.id, scene.id, file_name="mine.jpg")
        _create_task(db_session, other_user.id, scene.id, file_name="theirs.jpg")

        result = history_service.get_tasks(db_session, create_test_user.id)
        assert result["total"] == 1
        assert result["items"][0]["file_name"] == "mine.jpg"


class TestHistoryTaskDetail:
    """任务详情测试"""

    def test_get_task_detail_success(self, db_session, create_test_user):
        """获取自己任务详情成功"""
        scene = _create_scene(db_session, name="scene_detail")
        task = _create_task(db_session, create_test_user.id, scene.id)

        detail = history_service.get_task_detail(db_session, task.id, create_test_user.id)
        assert detail is not None
        assert detail["id"] == task.id

    def test_get_task_detail_not_found(self, db_session, create_test_user):
        """查询不存在的任务详情返回 None"""
        detail = history_service.get_task_detail(db_session, 9999, create_test_user.id)
        assert detail is None


class TestHistoryDelete:
    """删除测试"""

    def test_delete_own_task(self, db_session, create_test_user):
        """删除自己的任务成功"""
        scene = _create_scene(db_session, name="scene_del")
        task = _create_task(db_session, create_test_user.id, scene.id)

        result = history_service.delete_task(db_session, task.id, create_test_user.id)
        assert result is True

    def test_delete_nonexistent_task(self, db_session, create_test_user):
        """删除不存在的任务返回 False"""
        result = history_service.delete_task(db_session, 9999, create_test_user.id)
        assert result is False

    def test_cannot_delete_others_task(self, db_session, create_test_user):
        """不能删除别人的任务"""
        from app.entity.db_models import User
        from app.core.security import hash_password

        scene = _create_scene(db_session, name="scene_del2")
        other_user = User(
            username="other_del", email="other_del@example.com",
            hashed_password=hash_password("Test123456"), is_active=True
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        task = _create_task(db_session, other_user.id, scene.id)
        result = history_service.delete_task(db_session, task.id, create_test_user.id)
        assert result is False
