"""
检测 API 集成测试
使用 Mock 替代 detection_service，测试 API 端点、参数验证、认证拦截
"""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def _get_auth_headers(client: TestClient, test_user_data: dict) -> dict:
    """登录获取认证头"""
    login_resp = client.post("/api/auth/login", json={
        "username": test_user_data["username"],
        "password": test_user_data["password"],
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestDetectionAuthRequired:
    """认证拦截测试"""

    def test_single_no_token_rejected(self, client: TestClient):
        """无 Token 访问单图检测返回 401"""
        response = client.post(
            "/api/detection/single",
            data={"scene_id": "1"},
            files={"file": ("test.jpg", b"fake_image_data", "image/jpeg")},
        )
        assert response.status_code == 401

    def test_batch_no_token_rejected(self, client: TestClient):
        """无 Token 访问批量检测返回 401"""
        response = client.post(
            "/api/detection/batch",
            data={"scene_id": "1"},
            files=[("files", ("test.jpg", b"fake", "image/jpeg"))],
        )
        assert response.status_code == 401

    def test_video_no_token_rejected(self, client: TestClient):
        """无 Token 访问视频检测返回 401"""
        response = client.post(
            "/api/detection/video",
            data={"scene_id": "1"},
            files={"file": ("test.mp4", b"fake", "video/mp4")},
        )
        assert response.status_code == 401

    def test_get_task_no_token_rejected(self, client: TestClient):
        """无 Token 获取检测任务返回 401"""
        response = client.get("/api/detection/tasks/1")
        assert response.status_code == 401

    def test_get_alerts_no_token_rejected(self, client: TestClient):
        """无 Token 获取预警列表返回 401"""
        response = client.get("/api/detection/alerts")
        assert response.status_code == 401


class TestDetectionSingleAPI:
    """单图检测 API 测试（Mock detection_service）"""

    @patch("app.api.detection.detection_service")
    def test_detect_single_success(self, mock_service, client: TestClient, create_test_user, test_user_data):
        """Mock 单图检测成功返回 200"""
        mock_task = MagicMock()
        mock_task.id = 1
        mock_task.fire_level = "safe"
        mock_task.fire_object_count = 0
        mock_task.smoke_object_count = 0
        mock_task.annotated_url = "http://minio/annotated.jpg"
        mock_service.detect_single.return_value = mock_task

        headers = _get_auth_headers(client, test_user_data)
        response = client.post(
            "/api/detection/single",
            headers=headers,
            data={"scene_id": "1"},
            files={"file": ("test.jpg", b"fake_image", "image/jpeg")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["fire_level"] == "safe"

    @patch("app.api.detection.detection_service")
    def test_detect_single_missing_scene_id(self, mock_service, client: TestClient, create_test_user, test_user_data):
        """缺少 scene_id 参数返回 422"""
        headers = _get_auth_headers(client, test_user_data)
        response = client.post(
            "/api/detection/single",
            headers=headers,
            files={"file": ("test.jpg", b"fake_image", "image/jpeg")},
        )
        assert response.status_code == 422


class TestDetectionAlertsAPI:
    """预警列表 API 测试"""

    @patch("app.services.alert_service.alert_service")
    def test_get_alerts_success(self, mock_alert_svc, client: TestClient, create_test_user, test_user_data):
        """获取预警列表成功"""
        mock_alert_svc.get_alerts.return_value = []

        headers = _get_auth_headers(client, test_user_data)
        response = client.get("/api/detection/alerts", headers=headers)
        assert response.status_code == 200
        assert response.json()["code"] == 200
