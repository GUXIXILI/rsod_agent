# 火灾烟雾智能检测平台

基于 YOLOv11 的火灾烟雾智能检测平台，支持单图检测、批量ZIP检测和视频检测，集成 AI 对话辅助分析与火情预警功能。

## 技术栈

- **后端**：FastAPI + LangChain + SQLAlchemy + Alembic
- **前端**：Vue 3 + Vite + Element Plus
- **基础设施**：PostgreSQL（+pgvector）+ Redis + MinIO
- **AI 模型**：YOLO11n（火灾烟雾检测）+ DeepSeek / Qwen（LLM 对话）

## 环境要求

- Python 3.10+
- Node.js 18+
- Docker Desktop（用于启动 PostgreSQL / Redis / MinIO）

## 部署方式

本项目提供两种部署方式，可根据实际需求选择：

| 部署方式 | 说明 |
|----------|------|
| **源码部署（推荐）** | 后端和前端通过源码启动，基础设施使用 Docker，适合开发和调试 |
| **云端 API 服务** | 后端连接阿里云百炼等云端 LLM API，无需本地部署大模型，适合资源有限的机器 |

### 源码部署（推荐）

**Step 1：进入项目目录**

```bash
cd rsod_agent
```

**Step 2：启动基础设施服务**

```bash
docker compose up -d
```

| 服务 | 端口 | 说明 |
|------|------|------|
| PostgreSQL | 5433 | 数据库（含 pgvector 扩展） |
| Redis | 6379 | 缓存 |
| MinIO | 9000 / 9001 | 对象存储（9001 为管理控制台） |

**Step 3：后端部署**

```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # Linux / Mac
pip install -r requirements.txt
python tools/configure_env.py    # 交互式生成 .env 配置文件
alembic upgrade head             # 初始化数据库
python main.py                   # 启动后端服务
```

后端默认运行在 `http://localhost:8000`。

**Step 4：前端部署（新开终端）**

```bash
cd frontend
npm install
npm run dev
```

**Step 5：访问系统**

浏览器打开 [http://localhost:5173](http://localhost:5173)

### 云端 API 服务

适用于本地机器资源有限、不想本地部署大模型的场景。后端连接阿里云百炼等云端 LLM API，基础设施仍使用本地 Docker。

**Step 1-2：** 同源码部署（进入目录 + 启动基础设施）。

**Step 3：** 配置云端 API — 运行 `python tools/configure_env.py` 选择"阿里云百炼（Qwen）"，或手动编辑 `backend/.env`：

```env
QWEN_API_KEY=sk-your-api-key
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus
```

**Step 4-5：** 同源码部署（启动后端和前端）。

> 更多云端部署细节可参考 `docs/deploy_cloud_api.md`。

## LLM 配置参考

编辑 `backend/.env` 文件配置 LLM，支持多种 OpenAI 兼容 API：

| LLM 提供商 | QWEN_BASE_URL | QWEN_MODEL | 获取方式 |
|------------|--------------|------------|---------|
| DeepSeek | `https://api.deepseek.com` | `deepseek-chat` | [platform.deepseek.com](https://platform.deepseek.com) |
| 阿里云百炼 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` | [dashscope.console.aliyun.com](https://dashscope.console.aliyun.com) |
| 火山引擎 | `https://ark.cn-beijing.volces.com/api/v3` | 你部署的端点 ID | [console.volcengine.com](https://console.volcengine.com) |

其他常用配置项：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `DB_PORT` | 5433 | PostgreSQL 端口 |
| `REDIS_PORT` | 6379 | Redis 端口 |
| `MINIO_ENDPOINT` | localhost:9000 | MinIO 地址 |
| `JWT_SECRET_KEY` | （空） | JWT 密钥，建议设置 32 位以上随机字符串 |
| `DEFAULT_MODEL_PATH` | （空） | YOLO 模型权重路径 |

完整环境变量模板见 `backend/.env.example`。

## YOLO 模型获取

项目使用专用火灾烟雾检测模型 `best.pt`，需手动获取：

1. 从项目 GitHub Release 页面下载 `best.pt` 模型文件
2. 将文件放入 `backend/models/fire_smoke_yolo11n_v1/` 目录
3. 在 `.env` 中配置路径：`DEFAULT_MODEL_PATH=models/fire_smoke_yolo11n_v1/best.pt`

> 如果没有专用模型，系统会尝试自动下载 `yolov11n.pt` 通用模型，但该模型不具备火灾烟雾检测能力，检测效果会大打折扣。

## 默认账号

系统不提供默认管理员账号，首次使用请在前端页面注册新用户。

## 项目结构

项目分为 `backend/`（FastAPI 后端）、`frontend/`（Vue 3 前端）、`docs/`（部署文档）三个主要目录，基础设施编排通过 `docker-compose.yml` 管理。后端入口为 `backend/main.py`，前端开发服务器通过 `npm run dev` 启动。