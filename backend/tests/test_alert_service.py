"""
预警服务单元测试
覆盖 safe 不触发、notice/warning/danger 触发、预警处理标记
"""
from datetime import datetime

import pytest

from app.entity.db_models import DetectionScene, DetectionTask, FireAlert
from app.services.alert_service import AlertService, alert_service


def _create_scene(db_session, name="alert_scene"):
    scene = DetectionScene(
        name=name, display_name="预警测试场景", category="fire",
        class_names=["fire", "smoke"]
    )
    db_session.add(scene)
    db_session.commit()
    db_session.refresh(scene)
    return scene


def _create_task(db_session, user_id, scene_id):
    task = DetectionTask(
        user_id=user_id,
        scene_id=scene_id,
        task_type="single",
        file_name="alert_test.jpg",
        status="completed",
        detected_at=datetime.now(),
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


class TestAlertNotTriggeredForSafe:
    """safe 等级不触发预警"""

    def test_safe_no_alert(self, db_session, create_test_user):
        """safe 等级不生成预警记录"""
        scene = _create_scene(db_session, name="alert_safe")
        task = _create_task(db_session, create_test_user.id, scene.id)

        fire_level_result = {
            "fire_level": "safe",
            "fire_area": 0.0,
            "smoke_area": 0.0,
            "fire_object_count": 0,
            "smoke_object_count": 0,
            "suggestion": "当前无火情",
        }
        result = alert_service.create_alert(db_session, task, fire_level_result)
        assert result is None


class TestAlertTriggered:
    """notice/warning/danger 触发预警"""

    def test_notice_creates_alert(self, db_session, create_test_user):
        """notice 等级生成预警"""
        scene = _create_scene(db_session, name="alert_notice")
        task = _create_task(db_session, create_test_user.id, scene.id)

        fire_level_result = {
            "fire_level": "notice", "fire_area": 0.0, "smoke_area": 0.06,
            "fire_object_count": 0, "smoke_object_count": 1, "suggestion": "",
        }
        alert = alert_service.create_alert(db_session, task, fire_level_result)
        assert alert is not None
        assert alert.fire_level == "notice"
        assert alert.handled_status == "unhandled"

    def test_warning_creates_alert(self, db_session, create_test_user):
        """warning 等级生成预警"""
        scene = _create_scene(db_session, name="alert_warning")
        task = _create_task(db_session, create_test_user.id, scene.id)

        fire_level_result = {
            "fire_level": "warning", "fire_area": 0.05, "smoke_area": 0.0,
            "fire_object_count": 1, "smoke_object_count": 0, "suggestion": "",
        }
        alert = alert_service.create_alert(db_session, task, fire_level_result)
        assert alert is not None
        assert alert.fire_level == "warning"
        assert "现场核查" in alert.suggestion

    def test_danger_creates_alert(self, db_session, create_test_user):
        """danger 等级生成预警"""
        scene = _create_scene(db_session, name="alert_danger")
        task = _create_task(db_session, create_test_user.id, scene.id)

        fire_level_result = {
            "fire_level": "danger", "fire_area": 0.2, "smoke_area": 0.1,
            "fire_object_count": 3, "smoke_object_count": 2, "suggestion": "",
        }
        alert = alert_service.create_alert(db_session, task, fire_level_result)
        assert alert is not None
        assert alert.fire_level == "danger"
        assert "119" in alert.suggestion


class TestAlertDispatch:
    """预警推送状态流转测试"""

    def test_dispatch_sets_push_status(self, db_session, create_test_user):
        """_dispatch_alert 后 alert.push_status 为 dispatched"""
        scene = _create_scene(db_session, name="alert_dispatch_status")
        task = _create_task(db_session, create_test_user.id, scene.id)

        fire_level_result = {
            "fire_level": "warning", "fire_area": 0.05, "smoke_area": 0.0,
            "fire_object_count": 1, "smoke_object_count": 0, "suggestion": "",
        }
        alert = alert_service.create_alert(db_session, task, fire_level_result)
        assert alert.push_status == "dispatched"

    def test_dispatch_sets_pushed_at(self, db_session, create_test_user):
        """_dispatch_alert 后 alert.pushed_at 非 None"""
        scene = _create_scene(db_session, name="alert_dispatch_time")
        task = _create_task(db_session, create_test_user.id, scene.id)

        fire_level_result = {
            "fire_level": "danger", "fire_area": 0.2, "smoke_area": 0.1,
            "fire_object_count": 3, "smoke_object_count": 2, "suggestion": "",
        }
        alert = alert_service.create_alert(db_session, task, fire_level_result)
        assert alert.pushed_at is not None

    def test_dispatch_notice_level(self, db_session, create_test_user):
        """notice 等级也触发推送状态更新"""
        scene = _create_scene(db_session, name="alert_dispatch_notice")
        task = _create_task(db_session, create_test_user.id, scene.id)

        fire_level_result = {
            "fire_level": "notice", "fire_area": 0.0, "smoke_area": 0.06,
            "fire_object_count": 0, "smoke_object_count": 1, "suggestion": "",
        }
        alert = alert_service.create_alert(db_session, task, fire_level_result)
        assert alert.push_status == "dispatched"
        assert alert.pushed_at is not None


class TestAlertHandle:
    """预警处理标记测试"""

    def test_handle_alert_success(self, db_session, create_test_user):
        """标记预警为已处理"""
        scene = _create_scene(db_session, name="alert_handle")
        task = _create_task(db_session, create_test_user.id, scene.id)

        fire_level_result = {
            "fire_level": "warning", "fire_area": 0.05, "smoke_area": 0.0,
            "fire_object_count": 1, "smoke_object_count": 0, "suggestion": "",
        }
        alert = alert_service.create_alert(db_session, task, fire_level_result)

        handled = alert_service.handle_alert(db_session, alert.id)
        assert handled.handled_status == "resolved"
        assert handled.handled_at is not None

    def test_handle_nonexistent_alert(self, db_session):
        """处理不存在的预警抛出 ValueError"""
        with pytest.raises(ValueError, match="预警不存在"):
            alert_service.handle_alert(db_session, 9999)


class TestAlertGetAlerts:
    """获取预警列表测试"""

    def test_get_alerts_for_user(self, db_session, create_test_user):
        """获取用户关联的预警列表"""
        scene = _create_scene(db_session, name="alert_list")
        task = _create_task(db_session, create_test_user.id, scene.id)

        fire_level_result = {
            "fire_level": "notice", "fire_area": 0.0, "smoke_area": 0.06,
            "fire_object_count": 0, "smoke_object_count": 1, "suggestion": "",
        }
        alert_service.create_alert(db_session, task, fire_level_result)

        alerts = alert_service.get_alerts(db_session, create_test_user.id)
        assert len(alerts) >= 1
        assert alerts[0].fire_level == "notice"

    def test_get_alerts_filter_by_scene(self, db_session, create_test_user):
        """按场景 ID 筛选预警"""
        scene1 = _create_scene(db_session, name="alert_filter1")
        scene2 = _create_scene(db_session, name="alert_filter2")
        task1 = _create_task(db_session, create_test_user.id, scene1.id)
        task2 = _create_task(db_session, create_test_user.id, scene2.id)

        fl = {"fire_level": "warning", "fire_area": 0.05, "smoke_area": 0.0,
              "fire_object_count": 1, "smoke_object_count": 0, "suggestion": ""}
        alert_service.create_alert(db_session, task1, fl)
        alert_service.create_alert(db_session, task2, fl)

        alerts = alert_service.get_alerts(db_session, create_test_user.id, scene_id=scene1.id)
        assert all(a.scene_id == scene1.id for a in alerts)
