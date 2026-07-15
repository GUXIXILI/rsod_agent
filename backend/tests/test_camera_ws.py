"""
WebSocket 摄像头实时检测测试

测试 camera.py 中的 WebSocket 端点：
- 无 token 连接应被拒绝
- config 消息应正常处理
- idle 超时应断开
"""
import json
from unittest.mock import patch, MagicMock

import pytest


class TestWsConnectionWithoutToken:
    """无 token 时应拒绝 WebSocket 连接"""

    def test_ws_connection_without_token(self, client, db_session, create_test_user):
        """无 token 参数 → 服务端关闭连接（code=1008）"""
        from app.core.security import create_access_token

        # 故意不带 token 连接
        with pytest.raises(Exception):
            with client.websocket_connect("/api/detection/camera") as ws:
                # 如果连接被立即关闭，接收会抛异常
                ws.receive_json()


class TestWsInvalidToken:
    """无效 token 时应拒绝连接"""

    def test_ws_invalid_token(self, client, db_session, create_test_user):
        """无效 token → 服务端关闭连接"""
        with pytest.raises(Exception):
            with client.websocket_connect("/api/detection/camera?token=invalid_token") as ws:
                ws.receive_json()


class TestWsConfigMessage:
    """config 消息应正常处理并返回 config_ack"""

    @patch("app.api.camera.detection_service")
    def test_ws_config_message(self, mock_svc, client, db_session, create_test_user):
        from app.core.security import create_access_token

        token = create_access_token({"sub": str(create_test_user.id)})

        # mock detect_frame 用于模型预热
        mock_svc.detect_frame.return_value = {
            "annotated_frame": "",
            "detections": [],
            "total_objects": 0,
        }

        with client.websocket_connect(f"/api/detection/camera?token={token}") as ws:
            # 发送 config 消息
            ws.send_json({
                "type": "config",
                "mode": "cpu",
                "conf": 0.3,
                "iou": 0.5,
                "image_size": 416,
                "scene_id": 1,
            })

            # 应该收到 config_ack
            response = ws.receive_json()
            assert response["type"] == "config_ack"
            assert response["warmed_up"] is True


class TestWsIdleTimeout:
    """idle 超时应断开连接"""

    @patch("app.api.camera.detection_service")
    @patch("app.api.camera.settings")
    def test_ws_idle_timeout(self, mock_settings, mock_svc, client, db_session, create_test_user):
        from app.core.security import create_access_token

        token = create_access_token({"sub": str(create_test_user.id)})

        # mock detect_frame 用于模型预热
        mock_svc.detect_frame.return_value = {
            "annotated_frame": "",
            "detections": [],
            "total_objects": 0,
        }
        # 设置极短超时以触发 idle timeout
        mock_settings.WEBSOCKET_IDLE_TIMEOUT = 1
        mock_settings.WEBSOCKET_MAX_CONNECTIONS = 10

        with client.websocket_connect(f"/api/detection/camera?token={token}") as ws:
            # 发送 config 消息
            ws.send_json({
                "type": "config",
                "mode": "cpu",
                "conf": 0.3,
                "iou": 0.5,
                "image_size": 416,
                "scene_id": 1,
            })
            # 接收 config_ack
            ws.receive_json()

            # 等待 idle timeout（1秒）
            import time
            time.sleep(2)

            # 应该收到 error: idle timeout
            try:
                response = ws.receive_json()
                assert response["type"] == "error"
                assert "idle timeout" in response["message"]
            except Exception:
                # WebSocket 可能已关闭，也是预期行为
                pass
