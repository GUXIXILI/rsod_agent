FROM python:3.11-slim

# 工作目录设置为 backend/，使得 Python 可以直接导入 app 包和 main 模块
# backend/main.py 内部使用 from app.config.settings 等相对导入，需要 app 在 sys.path 中
WORKDIR /app/backend

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 优先安装 PyTorch CPU 版（避免网络不稳定时 torch 安装失败）
RUN pip install --no-cache-dir \
    torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu

# 复制并安装 Python 依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir \
    -r requirements.txt \
    -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com

# 复制后端代码到当前 WORKDIR（/app/backend/）
COPY backend/ ./

# 暴露端口
EXPOSE 8000

# 启动命令（WORKDIR 为 /app/backend，uvicorn 直接使用 main:app）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]