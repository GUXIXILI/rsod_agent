"""
管理员接口测试
覆盖：管理员获取用户列表、非管理员403、启禁用用户、获取模型列表
"""
import pytest
from fastapi.testclient import TestClient

from app.entity.db_models import User, Role, UserRole, DetectionScene, ModelVersion
from app.core.security import hash_password


def _make_admin(db_session, user: User) -> None:
    """辅助：将用户设为超级管理员"""
    user.is_superuser = True
    db_session.commit()
    db_session.refresh(user)


def _login(client: TestClient, test_user_data: dict) -> str:
    """辅助：登录并返回 access_token"""
    resp = client.post("/api/auth/login", json={
        "username": test_user_data["username"],
        "password": test_user_data["password"],
    })
    return resp.json()["access_token"]


class TestAdminListUsers:
    """管理员获取用户列表"""

    def test_admin_list_users(self, client: TestClient, db_session, create_test_user, test_user_data):
        """管理员获取用户列表成功"""
        _make_admin(db_session, create_test_user)
        token = _login(client, test_user_data)

        response = client.get("/api/admin/users", headers={
            "Authorization": f"Bearer {token}",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "items" in data["data"]
        assert data["data"]["total"] >= 1

    def test_non_admin_forbidden(self, client: TestClient, create_test_user, test_user_data):
        """非管理员访问管理员接口应返回403"""
        token = _login(client, test_user_data)
        response = client.get("/api/admin/users", headers={
            "Authorization": f"Bearer {token}",
        })
        assert response.status_code == 403


class TestAdminToggleUserStatus:
    """管理员启禁用用户"""

    def test_admin_toggle_user_status(self, client: TestClient, db_session, create_test_user, test_user_data):
        """管理员禁用/启用另一个用户"""
        _make_admin(db_session, create_test_user)
        token = _login(client, test_user_data)

        # 创建另一个用户来操作
        other = User(
            username="victim",
            email="victim@example.com",
            hashed_password=hash_password("Test123456"),
            is_active=True,
        )
        db_session.add(other)
        db_session.commit()
        db_session.refresh(other)

        # 禁用用户
        response = client.put(f"/api/admin/users/{other.id}/status", json={
            "is_active": False,
        }, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["is_active"] is False

        # 重新启用用户
        response = client.put(f"/api/admin/users/{other.id}/status", json={
            "is_active": True,
        }, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["data"]["is_active"] is True


class TestAdminListModels:
    """管理员获取模型列表"""

    def test_admin_list_models(self, client: TestClient, db_session, create_test_user, test_user_data):
        """管理员获取模型列表（可为空列表）"""
        _make_admin(db_session, create_test_user)
        token = _login(client, test_user_data)

        response = client.get("/api/admin/models", headers={
            "Authorization": f"Bearer {token}",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert isinstance(data["data"], list)
