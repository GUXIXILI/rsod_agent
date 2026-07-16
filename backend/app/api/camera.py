"""
摄像头实时检测 WebSocket 路由

通过 WebSocket 接收摄像头帧数据，执行 YOLOv11 推理并回传标注结果。
- WebSocket /api/detection/camera — 摄像头实时检测
"""
import asyncio
import base64
import json
import time

import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config.settings import settings
from app.core.logger import get_logger
from app.services.detection_service import detection_service

logger = get_logger(__name__)

router = APIRouter(tags=["camera"])

# 模块级连接计数器
_active_connections = 0


@router.websocket("/api/detection/camera")
async def camera_websocket(websocket: WebSocket):
    """摄像头实时检测 WebSocket 端点

    通信协议：
    1. 客户端发送 config 消息配置检测参数
    2. 客户端循环发送 frame 消息（base64 编码的 JPEG 帧）
    3. 服务端返回 result 消息（标注帧 + 检测结果 + FPS）
    """
    global _active_connections

    # ── 连接数限制检查 ──────────────────────────────────────────────────────
    if _active_connections >= settings.WEBSOCKET_MAX_CONNECTIONS:
        await websocket.close(code=1013, reason="too many connections")
        logger.warning("WebSocket 连接被拒绝：已达最大连接数 %d", settings.WEBSOCKET_MAX_CONNECTIONS)
        return

    await websocket.accept()
    _active_connections += 1
    logger.info("WebSocket 摄像头连接已建立: active=%d", _active_connections)

    # 检测参数默认值（等待 config 消息更新）
    device = "cpu"
    conf = 0.25
    iou = 0.45
    image_size = 640
    scene_id = 1
    warmed_up = False

    # FPS 计算
    fps_counter = 0
    fps_start = time.time()
    fps = 0.0

    try:
        while True:
            # ── Idle 超时：60 秒无帧自动断开 ─────────────────────────────────
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=float(settings.WEBSOCKET_IDLE_TIMEOUT),
                )
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "error", "message": "idle timeout"})
                logger.info("WebSocket 摄像头 idle 超时断开")
                break

            # ── 解析消息 ─────────────────────────────────────────────────────
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "invalid JSON"})
                continue

            msg_type = msg.get("type", "")

            # ── Config 消息：配置检测参数 + 模型预热 ──────────────────────────
            if msg_type == "config":
                mode = msg.get("mode", "cpu")
                conf = float(msg.get("conf", 0.25))
                iou = float(msg.get("iou", 0.45))
                image_size = int(msg.get("image_size", 640))
                scene_id = int(msg.get("scene_id", 1))

                # GPU / CPU 设备映射
                if mode == "gpu":
                    device = "0"
                else:
                    device = "cpu"
                    # CPU 模式自动降低 image_size 加速推理
                    if image_size > 416:
                        image_size = 416

                logger.info(
                    "WebSocket config: mode=%s, device=%s, conf=%.2f, "
                    "iou=%.2f, image_size=%d, scene_id=%d",
                    mode, device, conf, iou, image_size, scene_id,
                )

                # 模型预热：用哑帧触发模型加载和 CUDA 编译
                try:
                    dummy = np.zeros((480, 640, 3), dtype=np.uint8)
                    _, dummy_buf = cv2_imencode(dummy)
                    await asyncio.to_thread(
                        detection_service.detect_frame,
                        dummy_buf, scene_id, conf, iou, image_size, device,
                    )
                    warmed_up = True
                    logger.info("模型预热完成")
                except Exception as e:
                    logger.error("模型预热失败: error=%s", e)
                    await websocket.send_json({"type": "error", "message": f"warmup failed: {e}"})
                    continue

                await websocket.send_json({
                    "type": "config_ok",
                    "device": device,
                    "image_size": image_size,
                    "warmed_up": warmed_up,
                })

            # ── Frame 消息：接收帧 → 推理 → 回传结果 ─────────────────────────
            elif msg_type == "frame":
                if not warmed_up:
                    await websocket.send_json({
                        "type": "error",
                        "message": "not configured, send config first",
                    })
                    continue

                frame_b64 = msg.get("data", "")
                if not frame_b64:
                    await websocket.send_json({"type": "error", "message": "empty frame data"})
                    continue

                frame_bytes = base64.b64decode(frame_b64)

                # 在线程中执行推理（避免阻塞事件循环）
                t0 = time.time()
                try:
                    result = await asyncio.to_thread(
                        detection_service.detect_frame,
                        frame_bytes, scene_id, conf, iou, image_size, device,
                    )
                except Exception as e:
                    logger.error("帧推理失败: error=%s", e)
                    await websocket.send_json({"type": "error", "message": f"detect failed: {e}"})
                    continue

                inference_ms = int((time.time() - t0) * 1000)

                # FPS 计算
                fps_counter += 1
                elapsed = time.time() - fps_start
                if elapsed >= 1.0:
                    fps = fps_counter / elapsed
                    fps_counter = 0
                    fps_start = time.time()

                # 构造响应
                result["type"] = "result"
                result["fps"] = round(fps, 1)
                result["inference_time"] = inference_ms
                await websocket.send_json(result)

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"unknown message type: {msg_type}",
                })

    except WebSocketDisconnect:
        logger.info("WebSocket 摄像头正常断开")
    except Exception as e:
        logger.exception("WebSocket 摄像头异常断开: error=%s", e)
        try:
            await websocket.send_json({"type": "error", "message": f"server error: {e}"})
        except Exception:
            pass
    finally:
        _active_connections -= 1
        logger.info(
            "WebSocket 摄像头连接已关闭: active=%d", _active_connections
        )


def cv2_imencode(frame: np.ndarray) -> tuple:
    """辅助函数：将 numpy 帧编码为 JPEG 字节，返回 (success, buffer_bytes)"""
    import cv2
    success, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
    return success, buf.tobytes()
