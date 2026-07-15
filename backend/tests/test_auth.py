"""
认证接口测试
覆盖注册、登录（用户名/邮箱）、错误密码、不存在的用户、Token 获取用户等场景
"""
import pytest
from fastapi.testclient import TestClient


class TestAuthRegister:
    """用户注册测试"""

    def test_register_success(self, client: TestClient):
        """测试注册成功，返回 201"""
        response = client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "Test123456",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        # 密码不应返回
        assert "hashed_password" not in data

    def test_register_duplicate_username(self, client: TestClient, test_user_data):
        """测试重复用户名注册返回 400"""
        # 先注册一个用户
        client.post("/api/auth/register", json=test_user_data)
        # 再注册相同用户名
        response = client.post("/api/auth/register", json=test_user_data)
        assert response.status_code == 400
        data = response.json()
        assert "用户名" in data["message"] or "已存在" in data["message"]

    def test_register_validation_error(self, client: TestClient):
        """测试参数验证失败（缺少必填字段）"""
        response = client.post("/api/auth/register", json={
            "username": "test",
        })
        assert response.status_code == 422


class TestAuthLogin:
    """用户登录测试"""

    def test_login_with_username(self, client: TestClient, create_test_user, test_user_data):
        """测试使用用户名登录成功"""
        response = client.post("/api/auth/login", json={
            "username": test_user_data["username"],
            "password": test_user_data["password"],
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_with_email(self, client: TestClient, create_test_user, test_user_data):
        """测试使用邮箱登录成功"""
        response = client.post("/api/auth/login", json={
            "username": test_user_data["email"],
            "password": test_user_data["password"],
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_wrong_password(self, client: TestClient, create_test_user, test_user_data):
        """测试错误密码登录返回 401"""
        response = client.post("/api/auth/login", json={
            "username": test_user_data["username"],
            "password": "wrongpassword",
        })
        assert response.status_code == 401
        data = response.json()
        assert "用户名或密码错误" in data["message"]

    def test_login_wrong_password_email(self, client: TestClient, create_test_user, test_user_data):
        """测试使用邮箱 + 错误密码登录返回 401"""
        response = client.post("/api/auth/login", json={
            "username": test_user_data["email"],
            "password": "wrongpassword",
        })
        assert response.status_code == 401
        data = response.json()
        assert "用户名或密码错误" in data["message"]


class TestAuthMe:
    """获取当前用户信息测试"""

    def test_get_current_user(self, client: TestClient, create_test_user, test_user_data):
        """测试使用有效 Token 获取用户信息"""
        # 先登录获取 token
        login_response = client.post("/api/auth/login", json={
            "username": test_user_data["username"],
            "password": test_user_data["password"],
        })
        token = login_response.json()["access_token"]

        # 使用 token 获取用户信息
        response = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]

    def test_get_current_user_no_token(self, client: TestClient):
        """测试无 Token 获取用户信息返回 401"""
        response = client.get("/api/auth/me")
        assert response.status_code == 401