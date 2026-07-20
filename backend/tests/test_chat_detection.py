import os
os.environ.pop("SSLKEYLOGFILE", None)
import requests
import json
import io
from PIL import Image, ImageDraw

# 1. 登录
login_resp = requests.post(
    "http://localhost:8000/api/auth/login",
    json={"username": "testuser_fix2", "password": "Test1234!"},
    timeout=10
)
print("Login status:", login_resp.status_code)
login_data = login_resp.json()
print("Login response:", json.dumps(login_data, ensure_ascii=False)[:500])
token = login_data.get("data", {}).get("access_token") or login_data.get("access_token")
headers = {"Authorization": f"Bearer {token}"}

# 2. 生成测试图片
img = Image.new("RGB", (640, 480), (20, 20, 20))
draw = ImageDraw.Draw(img)
for i in range(10):
    x, y = 100 + i * 40, 200 + (i % 3) * 30
    draw.rectangle([x, y, x + 60, y + 80], fill=(255, 100, 20))
img_bytes = io.BytesIO()
img.save(img_bytes, format="JPEG")
img_bytes.seek(0)

# 3. 上传图片到聊天
upload_resp = requests.post(
    "http://localhost:8000/api/chat/upload",
    headers=headers,
    files={"file": ("fire_test.jpg", img_bytes, "image/jpeg")},
    timeout=10
)
print("Upload status:", upload_resp.status_code)
print("Upload response:", upload_resp.text[:500])
upload_data = upload_resp.json()["data"]
file_info = {
    "url": upload_data["url"],
    "type": upload_data["type"],
    "name": upload_data["name"]
}

# 4. 创建会话
session_resp = requests.post(
    "http://localhost:8000/api/chat/sessions",
    headers=headers,
    json={"title": "测试检测标注图"},
    timeout=10
)
print("Session status:", session_resp.status_code)
session_id = session_resp.json()["data"]["id"]

# 5. SSE 流式请求
payload = {
    "session_id": session_id,
    "content": "检测这张图片",
    "files": [file_info]
}
print("SSE payload:", json.dumps(payload, ensure_ascii=False))

sse_resp = requests.post(
    "http://localhost:8000/api/chat/messages/stream",
    headers={**headers, "Accept": "text/event-stream"},
    json=payload,
    stream=True,
    timeout=60
)
print("SSE status:", sse_resp.status_code)

# 6. 解析 SSE 事件
current_event = None
for line in sse_resp.iter_lines():
    if not line:
        continue
    line = line.decode("utf-8")
    if line.startswith("event:"):
        current_event = line[6:].strip()
    elif line.startswith("data:"):
        data_str = line[5:].strip()
        try:
            data = json.loads(data_str)
            print("Event:", current_event, "Keys:", list(data.keys()))
            if current_event in ("tool_result", "tool_end"):
                result = data.get("result", "")
                print("Tool result preview:", result[:500])
                try:
                    result_obj = json.loads(result)
                    print("Has annotated_image_base64:", "annotated_image_base64" in result_obj)
                    print("Has annotated_image_url:", "annotated_image_url" in result_obj)
                    print("fire_object_count:", result_obj.get("fire_object_count"))
                    print("smoke_object_count:", result_obj.get("smoke_object_count"))
                except Exception as e:
                    print("Result is not JSON:", e)
            if current_event == "done":
                print("Done event received")
                print("Done data:", json.dumps(data, ensure_ascii=False, indent=2)[:1000])
                break
        except Exception as e:
            print("Parse error:", e, line[:200])
