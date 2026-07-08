"""
健康检查接口测试
测试 /api/health 和 /api/health/detail 两个端点
"""
from fastapi.testclient import TestClient


class TestHealthCheck:
    """健康检查测试类"""

    def test_root_path(self, client: TestClient):
        """测试根路径返回正确信息"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data

    def test_basic_health(self, client: TestClient):
        """测试基础健康检查返回 healthy 状态"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["status"] == "healthy"
        assert data["data"]["app_name"] == "GLW RSOD Agent Platform"

    def test_health_detail(self, client: TestClient):
        """测试详细健康检查返回各依赖状态"""
        response = client.get("/api/health/detail")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "dependencies" in data["data"]
        # 使用 SQLite 测试数据库时，PostgreSQL 检查会失败（unhealthy）
        assert "postgresql" in data["data"]["dependencies"]
        assert "redis" in data["data"]["dependencies"]
        assert "minio" in data["data"]["dependencies"]