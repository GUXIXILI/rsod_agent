"""
用户信息修改接口测试
覆盖：修改邮箱、重复邮箱、修改密码（正确/错误旧密码）
"""
import pytest
from fastapi.testclient import TestClient


def _login(client: TestClient, test_user_data: dict) -> str:
    """辅助：登录并返回 access_token"""
    resp = client.post("/api/auth/login", json={
        "username": test_user_data["username"],
        "password": test_user_data["password"],
    })
    return resp.json()["access_token"]


class TestUpdateProfile:
    """修改个人信息"""

    def test_update_profile_email(self, client: TestClient, create_test_user, test_user_data):
        """测试修改邮箱成功"""
        token = _login(client, test_user_data)
        response = client.put("/api/auth/profile", json={
            "email": "newemail@example.com",
        }, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["email"] == "newemail@example.com"

    def test_update_profile_duplicate_email(self, client: TestClient, db_session, create_test_user, test_user_data):
        """测试修改为已被其他用户占用的邮箱应拒绝"""
        from app.entity.db_models import User
        from app.core.security import hash_password

        # 创建另一个用户占用目标邮箱
        other = User(
            username="otheruser",
            email="occupied@example.com",
            hashed_password=hash_password("Test123456"),
            is_active=True,
        )
        db_session.add(other)
        db_session.commit()

        token = _login(client, test_user_data)
        response = client.put("/api/auth/profile", json={
            "email": "occupied@example.com",
        }, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 400


class TestChangePassword:
    """修改密码"""

    def test_change_password(self, client: TestClient, create_test_user, test_user_data):
        """测试使用正确旧密码修改密码"""
        token = _login(client, test_user_data)
        response = client.put("/api/auth/password", json={
            "old_password": test_user_data["password"],
            "new_password": "NewSecure789",
        }, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

        # 使用新密码登录验证
        login_resp = client.post("/api/auth/login", json={
            "username": test_user_data["username"],
            "password": "NewSecure789",
        })
        assert login_resp.status_code == 200

    def test_change_password_wrong_old(self, client: TestClient, create_test_user, test_user_data):
        """测试使用错误旧密码修改密码应拒绝"""
        token = _login(client, test_user_data)
        response = client.put("/api/auth/password", json={
            "old_password": "WrongOldPassword",
            "new_password": "NewSecure789",
        }, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 400
