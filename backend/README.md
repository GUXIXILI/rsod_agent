# Fire & Smoke Detection Platform 后端工程说明

　　本目录为火灾与烟雾智能检测平台后端工程，当前处于 Day02 项目初始化阶段。工程采用 FastAPI + SQLAlchemy + Alembic + PostgreSQL + Redis + MinIO 技术栈，已完成后端目录结构、全局配置、数据库连接、ORM 模型、Pydantic Schema、数据库迁移、MinIO 客户端、Docker Compose 基础设施、JWT 认证模块以及 main.py 入口。

## 工程结构

```
backend/
├── main.py                      # FastAPI 入口
├── requirements.txt             # Python 依赖
├── .env                         # 环境变量（已加入 .gitignore）
├── .env.example                 # 环境变量模板
├── alembic.ini                  # Alembic 配置文件
├── alembic/                     # 迁移脚本目录
│   ├── env.py
│   └── versions/
│       └── 9eb7c6321bba_init_create_all_15_tables.py
└── app/                         # 应用代码
    ├── api/                     # API 路由层
    │   └── auth.py              # 认证接口（注册/登录/当前用户）
    ├── config/                  # 配置模块
    │   └── settings.py          # 全局配置（pydantic-settings）
    ├── core/                    # 核心工具
    │   └── security.py          # JWT / bcrypt
    ├── database/                # 数据库连接
    │   └── session.py           # engine / SessionLocal / Base / get_db
    ├── entity/                  # 数据模型
    │   ├── db_models.py         # SQLAlchemy ORM 模型（14 张业务表）
    │   └── schemas.py           # Pydantic 请求/响应模型
    ├── services/                # 业务服务层
    │   └── user_service.py      # 用户注册/登录/鉴权
    └── storage/                 # 对象存储
        └── minio_client.py      # MinIO 客户端封装
```

## 当前完成度

| 模块 | 状态 | 关键产物 |
| ---- | ---- | -------- |
| 目录结构与模块划分 | 部分完成 | 各子包已创建；缺少 `app/__init__.py`，`app/config/detection.py`、`llm.py` 为后续天数预留 |
| 全局配置 | 已完成 | `app/config/settings.py`、`.env` |
| 数据库连接 | 已完成 | `app/database/session.py` |
| SQLAlchemy 数据模型 | 已完成 | `app/entity/db_models.py`（14 张业务表） |
| Pydantic 请求/响应模型 | 已完成 | `app/entity/schemas.py`（33 个模型类） |
| Alembic 数据库迁移 | 已完成 | `alembic.ini`、`alembic/env.py`、初始迁移版本已应用 |
| MinIO 存储客户端 | 已完成 | `app/storage/minio_client.py` |
| Docker Compose 基础设施 | 已完成 | `../docker-compose.yml`（postgres/redis/minio） |
| JWT 认证模块 | 已完成 | `app/core/security.py`、`app/services/user_service.py`、`app/api/auth.py` |
| main.py 入口与路由 | 已完成 | `main.py`（含 CORS、lifespan、health、auth_router） |
| 验证与测试 | 已完成 | 接口测试通过（注册/登录/me/health/Swagger） |

## 架构说明

　　后端采用经典分层架构：

1. API 层（`app/api/`）仅负责接收 HTTP 请求、参数校验和返回响应，不写业务逻辑。
2. Service 层（`app/services/`）封装核心业务逻辑，例如用户注册、登录、鉴权。
3. Entity 层（`app/entity/`）分为数据库模型（`db_models.py`）和 API 模型（`schemas.py`），前者面向持久化，后者面向接口序列化。
4. Database 层（`app/database/`）只负责创建引擎、会话工厂和提供 `get_db` 依赖。
5. Storage 层（`app/storage/`）独立封装 MinIO 对象存储操作。
6. Core 层（`app/core/`）提供 JWT、密码哈希等通用安全工具。

## 运行方式

### 1. 启动基础设施

　　在项目根目录执行：

```powershell
cd d:\clone\rsod_agent
docker compose up -d postgres redis minio
```

　　默认 PostgreSQL 映射到宿主机端口 `5433`，Redis 为 `6379`，MinIO API 为 `9000`、控制台为 `9001`。

### 2. 激活虚拟环境

```powershell
cd d:\clone\rsod_agent\backend
.venv\Scripts\activate.ps1
```

### 3. 应用数据库迁移

```powershell
.venv\Scripts\alembic.exe upgrade head
```

### 4. 启动后端服务

```powershell
.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8080
```

　　启动后访问：

- Swagger 文档：`http://localhost:8080/docs`
- ReDoc 文档：`http://localhost:8080/redoc`
- 健康检查：`http://localhost:8080/api/health`

### 5. 验证认证接口

```powershell
# 注册
curl.exe -X POST http://localhost:8080/api/auth/register `
  -H "Content-Type: application/json" `
  -d '{"username":"testuser","email":"test@example.com","password":"123456"}'

# 登录
curl.exe -X POST http://localhost:8080/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{"username":"testuser","password":"123456"}'

# 获取当前用户信息（将 TOKEN 替换为登录返回的 access_token）
curl.exe -X GET http://localhost:8080/api/auth/me `
  -H "Authorization: Bearer TOKEN"
```

## 注意事项

- `.env` 文件已被 `.gitignore` 忽略，新成员可从 `.env.example` 复制并修改。
- `.env.example` 中 `MINIO_BUCKET` 当前为 `fire-detection-images`，与 `.env` 一致，复制后可直接使用。
- `app/__init__.py` 当前缺失，Python 3 中仍可作为命名空间包导入，但建议补全以保持规范。
- 启动时可能出现 Pydantic 保护命名空间警告（`model_` 前缀字段），不影响运行，可通过设置 `model_config = {"protected_namespaces": ()}` 消除。
