"""
训练扩展接口测试
覆盖：验证不存在的任务、未完成训练拒绝导出、下载端点、预测端点
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.entity.db_models import DetectionScene, TrainingTask
from app.core.security import hash_password


def _login(client: TestClient, test_user_data: dict) -> str:
    """辅助：登录并返回 access_token"""
    resp = client.post("/api/auth/login", json={
        "username": test_user_data["username"],
        "password": test_user_data["password"],
    })
    return resp.json()["access_token"]


class TestValidateTraining:
    """验证训练结果"""

    def test_validate_nonexistent_task(self, client: TestClient, create_test_user, test_user_data):
        """不存在的训练任务应返回 404"""
        token = _login(client, test_user_data)
        response = client.post("/api/training/validate/nonexistent-uuid-12345", headers={
            "Authorization": f"Bearer {token}",
        })
        assert response.status_code == 404


class TestExportModel:
    """导出模型"""

    def test_export_task_not_completed(self, client: TestClient, db_session, create_test_user, test_user_data):
        """未完成的训练任务应拒绝导出"""
        token = _login(client, test_user_data)

        # 创建一个未完成的训练任务
        scene = DetectionScene(
            name="test_fire",
            display_name="测试火灾检测",
            category="fire",
            class_names=["fire", "smoke"],
            is_active=True,
        )
        db_session.add(scene)
        db_session.commit()
        db_session.refresh(scene)

        task = TrainingTask(
            user_id=create_test_user.id,
            scene_id=scene.id,
            task_uuid="test-running-uuid",
            status="running",
            model_name="yolov11n",
            epochs=100,
            img_size=640,
            batch_size=16,
            device="0",
        )
        db_session.add(task)
        db_session.commit()

        response = client.post("/api/training/export/test-running-uuid", json={
            "format": "onnx",
        }, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 400

    def test_export_nonexistent_task(self, client: TestClient, create_test_user, test_user_data):
        """不存在的训练任务应返回 404"""
        token = _login(client, test_user_data)
        response = client.post("/api/training/export/nonexistent-uuid-99999", json={
            "format": "onnx",
        }, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 404


class TestDownloadModel:
    """下载模型权重"""

    def test_download_nonexistent_task(self, client: TestClient, create_test_user, test_user_data):
        """不存在的训练任务应返回 404"""
        token = _login(client, test_user_data)
        response = client.get("/api/training/download/nonexistent-uuid-88888", headers={
            "Authorization": f"Bearer {token}",
        })
        assert response.status_code == 404


class TestPredictEndpoint:
    """单图预测"""

    def test_predict_nonexistent_task(self, client: TestClient, create_test_user, test_user_data):
        """不存在的训练任务应返回 404"""
        token = _login(client, test_user_data)
        response = client.post("/api/training/predict/nonexistent-uuid-77777",
            files={"file": ("test.jpg", b"\x00\x01\x02", "image/jpeg")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
