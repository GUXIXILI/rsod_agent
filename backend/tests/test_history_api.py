"""
历史记录 API 集成测试
测试分页参数传递、筛选参数、删除权限
"""
from datetime import datetime

from fastapi.testclient import TestClient

from app.entity.db_models import DetectionScene, DetectionTask


def _get_auth_headers(client: TestClient, test_user_data: dict) -> dict:
    """登录获取认证头"""
    login_resp = client.post("/api/auth/login", json={
        "username": test_user_data["username"],
        "password": test_user_data["password"],
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_test_data(db_session, user_id):
    """创建测试场景和任务数据"""
    scene = DetectionScene(
        name="hist_api_scene", display_name="API测试场景", category="fire",
        class_names=["fire", "smoke"]
    )
    db_session.add(scene)
    db_session.commit()
    db_session.refresh(scene)

    for i in range(5):
        task = DetectionTask(
            user_id=user_id,
            scene_id=scene.id,
            task_type="single",
            file_name=f"hist_test_{i}.jpg",
            status="completed",
            fire_level="danger" if i == 0 else "safe",
            fire_object_count=1 if i == 0 else 0,
            smoke_object_count=0,
            detected_at=datetime.now(),
        )
        db_session.add(task)
    db_session.commit()
    return scene


class TestHistoryAPIAuth:
    """认证拦截测试"""

    def test_get_tasks_no_token(self, client: TestClient):
        """无 Token 查询历史返回 401"""
        response = client.get("/api/history/tasks")
        assert response.status_code == 401

    def test_get_detail_no_token(self, client: TestClient):
        """无 Token 查询详情返回 401"""
        response = client.get("/api/history/tasks/1")
        assert response.status_code == 401

    def test_delete_no_token(self, client: TestClient):
        """无 Token 删除返回 401"""
        response = client.delete("/api/history/tasks/1")
        assert response.status_code == 401


class TestHistoryAPIPagination:
    """分页参数测试"""

    def test_default_pagination(self, client: TestClient, db_session, create_test_user, test_user_data):
        """默认分页参数"""
        _create_test_data(db_session, create_test_user.id)
        headers = _get_auth_headers(client, test_user_data)

        response = client.get("/api/history/tasks", headers=headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] == 5
        assert data["page"] == 1

    def test_custom_page_size(self, client: TestClient, db_session, create_test_user, test_user_data):
        """自定义 page_size"""
        _create_test_data(db_session, create_test_user.id)
        headers = _get_auth_headers(client, test_user_data)

        response = client.get("/api/history/tasks?page_size=2", headers=headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["items"]) == 2

    def test_invalid_page_number(self, client: TestClient, db_session, create_test_user, test_user_data):
        """无效页码（< 1）返回 422"""
        _create_test_data(db_session, create_test_user.id)
        headers = _get_auth_headers(client, test_user_data)

        response = client.get("/api/history/tasks?page=0", headers=headers)
        assert response.status_code == 422


class TestHistoryAPIFilters:
    """筛选参数测试"""

    def test_filter_by_fire_level(self, client: TestClient, db_session, create_test_user, test_user_data):
        """按火情等级筛选"""
        _create_test_data(db_session, create_test_user.id)
        headers = _get_auth_headers(client, test_user_data)

        response = client.get("/api/history/tasks?fire_level=danger", headers=headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] == 1
        assert data["items"][0]["fire_level"] == "danger"

    def test_filter_by_file_name(self, client: TestClient, db_session, create_test_user, test_user_data):
        """按文件名搜索"""
        _create_test_data(db_session, create_test_user.id)
        headers = _get_auth_headers(client, test_user_data)

        response = client.get("/api/history/tasks?file_name=hist_test_0", headers=headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] == 1


class TestHistoryAPIDelete:
    """删除权限测试"""

    def test_delete_own_task(self, client: TestClient, db_session, create_test_user, test_user_data):
        """删除自己的任务成功"""
        scene = _create_test_data(db_session, create_test_user.id)
        task = db_session.query(DetectionTask).filter(
            DetectionTask.user_id == create_test_user.id
        ).first()
        headers = _get_auth_headers(client, test_user_data)

        response = client.delete(f"/api/history/tasks/{task.id}", headers=headers)
        assert response.status_code == 200

    def test_delete_nonexistent_task(self, client: TestClient, db_session, create_test_user, test_user_data):
        """删除不存在的任务返回 404"""
        _create_test_data(db_session, create_test_user.id)
        headers = _get_auth_headers(client, test_user_data)

        response = client.delete("/api/history/tasks/99999", headers=headers)
        assert response.status_code == 404

    def test_cannot_delete_others_task(self, client: TestClient, db_session, create_test_user, test_user_data):
        """不能删除别人的任务"""
        from app.entity.db_models import User
        from app.core.security import hash_password

        other_user = User(
            username="hist_other", email="hist_other@example.com",
            hashed_password=hash_password("Test123456"), is_active=True
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        scene = _create_test_data(db_session, other_user.id)
        task = db_session.query(DetectionTask).filter(
            DetectionTask.user_id == other_user.id
        ).first()

        headers = _get_auth_headers(client, test_user_data)
        response = client.delete(f"/api/history/tasks/{task.id}", headers=headers)
        assert response.status_code == 404


class TestHistoryAPIDetail:
    """任务详情 API 测试"""

    def test_get_task_detail_success(self, client: TestClient, db_session, create_test_user, test_user_data):
        """获取自己任务详情成功"""
        _create_test_data(db_session, create_test_user.id)
        task = db_session.query(DetectionTask).filter(
            DetectionTask.user_id == create_test_user.id
        ).first()
        headers = _get_auth_headers(client, test_user_data)

        response = client.get(f"/api/history/tasks/{task.id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["data"]["id"] == task.id

    def test_get_nonexistent_task_detail(self, client: TestClient, db_session, create_test_user, test_user_data):
        """获取不存在的任务返回 404"""
        headers = _get_auth_headers(client, test_user_data)
        response = client.get("/api/history/tasks/99999", headers=headers)
        assert response.status_code == 404
