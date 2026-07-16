"""
文件代理接口测试
覆盖：未鉴权拦截、不在白名单的bucket、目录遍历攻击、文件不存在
"""
import pytest
from fastapi.testclient import TestClient


def _get_auth_headers(client: TestClient, test_user_data: dict) -> dict:
    """登录获取认证头"""
    login_resp = client.post("/api/auth/login", json={
        "username": test_user_data["username"],
        "password": test_user_data["password"],
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestFilesProxy:
    """MinIO 文件代理"""

    def test_proxy_file_no_token(self, client: TestClient):
        """未携带 Token 访问文件代理应返回 401"""
        response = client.get("/api/files/uploads/somefile.jpg")
        assert response.status_code == 401

    def test_proxy_file_invalid_bucket(self, client: TestClient, create_test_user, test_user_data):
        """不在白名单的 bucket 应返回 403"""
        headers = _get_auth_headers(client, test_user_data)
        response = client.get("/api/files/secret-bucket/somefile.jpg", headers=headers)
        assert response.status_code == 403
        data = response.json()
        assert data["code"] == 403

    def test_proxy_file_path_traversal(self, client: TestClient, create_test_user, test_user_data):
        """目录遍历（..）应返回 400 或被路由规范化拒绝（404）"""
        headers = _get_auth_headers(client, test_user_data)
        # 使用 %2e%2e 编码绕过路由规范化，直接测试路径安全校验
        response = client.get("/api/files/uploads/%2e%2e/%2e%2e/etc/passwd", headers=headers)
        # 框架可能返回 400（被安全检查拦截）或 404（路由未匹配）
        assert response.status_code in (400, 404)

    def test_proxy_file_not_found(self, client: TestClient, create_test_user, test_user_data):
        """文件不存在应返回 404（MinIO 不可用或文件不存在）"""
        headers = _get_auth_headers(client, test_user_data)
        response = client.get("/api/files/uploads/nonexistent_file_12345.jpg", headers=headers)
        # 由于测试环境 MinIO 不可用，会走到 except 分支返回 404
        assert response.status_code == 404
        data = response.json()
        assert data["code"] == 404
