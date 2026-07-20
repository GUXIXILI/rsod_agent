"""
集成测试：验证智能对话中图片检测会返回带标注框的可视化结果。

直接调用后端 /api/chat/messages/stream 接口，上传真实火灾图片，
解析 SSE 流，检查是否包含 annotated_image_base64 字段。
"""
import json
import os
from pathlib import Path

import requests


def _upload_image_to_minio(image_path: str) -> str:
    """把本地图片上传到后端，获取 MinIO URL"""
    backend = "http://localhost:8000"
    with open(image_path, "rb") as f:
        files = {"file": (os.path.basename(image_path), f, "image/png")}
        resp = requests.post(f"{backend}/api/upload", files=files, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    # 兼容 {code, data: {url, type, name}} 和 {url, type, name}
    payload = data.get("data", data)
    return payload["url"]


def _get_or_create_session() -> int:
    """获取第一个会话，若没有则创建新会话"""
    backend = "http://localhost:8000"
    token = _login()
    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get(f"{backend}/api/chat/sessions", headers=headers, timeout=30)
    resp.raise_for_status()
    sessions = resp.json().get("data", {}).get("items", [])
    if sessions:
        return sessions[0]["id"]

    resp = requests.post(
        f"{backend}/api/chat/sessions",
        headers=headers,
        json={"title": "可视化检测测试"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"]["id"]


def _login() -> str:
    """使用 admin 账号登录获取 token"""
    backend = "http://localhost:8000"
    resp = requests.post(
        f"{backend}/api/auth/login",
        json={"username": "admin", "password": "admin123"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"]["access_token"]


def test_chat_image_detection_returns_visual_result():
    """测试对话图片检测返回标注图"""
    backend = "http://localhost:8000"
    token = _login()
    headers = {"Authorization": f"Bearer {token}"}
    session_id = _get_or_create_session()

    # 使用项目根目录下的测试火灾图片
    image_path = Path(__file__).resolve().parent.parent / "test_fire_img.png"
    if not image_path.exists():
        raise FileNotFoundError(f"测试图片不存在: {image_path}")

    image_url = _upload_image_to_minio(str(image_path))

    payload = {
        "content": "帮我检测这张图片有没有火灾",
        "files": [{"url": image_url, "type": "image", "name": image_path.name}],
    }

    resp = requests.post(
        f"{backend}/api/chat/sessions/{session_id}/messages/stream",
        headers=headers,
        json=payload,
        stream=True,
        timeout=120,
    )
    resp.raise_for_status()

    found_visual = False
    found_summary = False
    for line in resp.iter_lines():
        if not line:
            continue
        line = line.decode("utf-8")
        if line.startswith("data:"):
            data_str = line[5:].strip()
            try:
                event = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            if event.get("event") in ("tool_result", "tool_end"):
                result = event.get("result", "")
                try:
                    parsed = json.loads(result)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict) and "detections" in parsed:
                    found_summary = True
                    if parsed.get("annotated_image_url") or parsed.get("annotated_image_base64"):
                        found_visual = True
                        print(f"检测到 {parsed.get('total_objects', 0)} 个目标，包含标注图")

    assert found_summary, "未收到检测结果事件"
    assert found_visual, "检测结果中未包含标注图 URL 或 base64"


if __name__ == "__main__":
    test_chat_image_detection_returns_visual_result()
    print("集成测试通过：对话图片检测返回了带标注框的可视化结果")
