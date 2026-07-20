import os
os.environ.pop("SSLKEYLOGFILE", None)
import requests
import json

# 1. 注册并登录获取 token
reg_resp = requests.post(
    "http://localhost:8000/api/auth/register",
    json={"username": "testuser_fix2", "password": "Test1234!", "email": "test_fix2@example.com"},
    timeout=10
)
print("Register status:", reg_resp.status_code, reg_resp.text[:100])

login_resp = requests.post(
    "http://localhost:8000/api/auth/login",
    json={"username": "testuser_fix2", "password": "Test1234!"},
    timeout=10
)
print("Login status:", login_resp.status_code)
if login_resp.status_code != 200:
    print(login_resp.text)
    exit(1)
token = login_resp.json().get("data", {}).get("access_token") or login_resp.json().get("access_token")
print("Token:", token[:30] + "...")

# 2. 生成一张测试图片（橙红色火焰状）
from PIL import Image, ImageDraw
import io
img = Image.new("RGB", (640, 480), (20, 20, 20))
draw = ImageDraw.Draw(img)
# 画一些橙红色矩形模拟火焰
for i in range(10):
    x, y = 100 + i * 40, 200 + (i % 3) * 30
    draw.rectangle([x, y, x + 60, y + 80], fill=(255, 100, 20))
img_bytes = io.BytesIO()
img.save(img_bytes, format="JPEG")
img_bytes = img_bytes.getvalue()
print("Generated test image size:", len(img_bytes))

# 3. 调用单图检测
headers = {"Authorization": f"Bearer {token}"}
files = {"file": ("fire_test.jpg", img_bytes, "image/jpeg")}
detect_resp = requests.post(
    "http://localhost:8000/api/detection/single",
    headers=headers,
    files=files,
    data={"scene_id": "1"},
    timeout=60
)
print("Detect status:", detect_resp.status_code)
result = detect_resp.json()
print(json.dumps(result, ensure_ascii=False, indent=2)[:2000])
