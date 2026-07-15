"""
密码重置接口测试
覆盖：生成重置令牌、使用令牌重置密码、过期令牌、已使用令牌、无效邮箱
"""
import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.entity.db_models import PasswordResetToken, User
from app.core.security import hash_password


class TestForgotPassword:
    """忘记密码 — 生成重置令牌"""

    def test_forgot_password(self, client: TestClient, create_test_user, test_user_data):
        """测试忘记密码：为已注册用户生成重置令牌"""
        response = client.post("/api/auth/forgot-password", json={
            "email": test_user_data["email"],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "token" in data["data"]

    def test_forgot_password_invalid_email(self, client: TestClient):
        """测试不存在的邮箱应返回错误"""
        response = client.post("/api/auth/forgot-password", json={
            "email": "nobody@example.com",
        })
        # 服务层抛出 404 HTTPException
        assert response.status_code == 404


class TestResetPassword:
    """重置密码 — 使用令牌"""

    def test_reset_password_valid(self, client: TestClient, create_test_user, test_user_data):
        """测试使用有效令牌重置密码"""
        # 1. 获取重置令牌
        resp = client.post("/api/auth/forgot-password", json={
            "email": test_user_data["email"],
        })
        token = resp.json()["data"]["token"]

        # 2. 使用令牌重置密码
        response = client.post("/api/auth/reset-password", json={
            "token": token,
            "new_password": "NewPass123456",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

        # 3. 使用新密码登录验证
        login_resp = client.post("/api/auth/login", json={
            "username": test_user_data["username"],
            "password": "NewPass123456",
        })
        assert login_resp.status_code == 200

    def test_reset_password_expired(self, client: TestClient, db_session, create_test_user, test_user_data):
        """测试过期令牌应拒绝"""
        # 手动插入一个已过期的重置令牌
        plain_token = "expired-test-token-abc123"
        token_hash = hashlib.sha256(plain_token.encode()).hexdigest()
        expired = PasswordResetToken(
            user_id=create_test_user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        db_session.add(expired)
        db_session.commit()

        response = client.post("/api/auth/reset-password", json={
            "token": plain_token,
            "new_password": "ShouldNotWork123",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 400  # 令牌无效或已过期

    def test_reset_password_used(self, client: TestClient, db_session, create_test_user, test_user_data):
        """测试已使用的令牌应拒绝"""
        plain_token = "used-test-token-xyz789"
        token_hash = hashlib.sha256(plain_token.encode()).hexdigest()
        used_token = PasswordResetToken(
            user_id=create_test_user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            used=True,
        )
        db_session.add(used_token)
        db_session.commit()

        response = client.post("/api/auth/reset-password", json={
            "token": plain_token,
            "new_password": "ShouldNotWork456",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 400
