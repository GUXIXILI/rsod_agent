from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.scenes import router as scenes_router
from app.core.logger import setup_logging, get_logger
from app.core.exceptions import register_exception_handlers
from app.middleware.request_logger import RequestLogMiddleware

# ── 初始化日志系统 ────────────────────────────────────
# 必须在创建 app 之前调用，确保后续所有模块的 logger 都已配置好
setup_logging()

logger = get_logger(__name__)

# 启动前安全检查：JWT 密钥必须配置
if not settings.JWT_SECRET_KEY or len(settings.JWT_SECRET_KEY) < 32:
    logger.error(
        "JWT_SECRET_KEY 未配置或长度不足 32 位，系统运行在极低安全模式下，"
        "请通过环境变量或 .env 文件配置强密钥。"
    )


def init_minio():
    """初始化 MinIO 存储桶（带超时保护，避免 MinIO 不可用时阻塞启动）"""
    import threading
    from app.storage.minio_client import MinIOClient

    result = {"success": False, "error": None}

    def _init():
        try:
            minio_client = MinIOClient()
            result["success"] = True
            print(f"MinIO 存储桶 '{minio_client.bucket_name}' 初始化完成")
        except Exception as e:
            result["error"] = str(e)

    thread = threading.Thread(target=_init, daemon=True)
    thread.start()
    thread.join(timeout=10)  # 最多等待 10 秒

    if not result["success"]:
        if result["error"]:
            print(f"MinIO 初始化失败（已跳过，不影响启动）: {result['error']}")
        else:
            print("MinIO 初始化超时（已跳过，不影响启动）")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("正在初始化服务...")
    init_minio()
    # 启动定时任务调度器
    from app.scheduler import start_scheduler
    start_scheduler()
    yield
    # 关闭时执行
    # 停止定时任务调度器
    from app.scheduler import stop_scheduler
    stop_scheduler()
    yield
    # 关闭时执行
    print("服务已关闭")


# 创建 FastAPI 实例
app = FastAPI(
    title="GLW Fire & Smoke Detection Platform",
    version="2.0.0",
    description="基于 YOLOv11 的火灾烟雾智能检测预警平台 API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── 注册全局异常处理器 ────────────────────────────────
# 统一捕获所有异常，返回标准 JSON 格式 {code, message, data}
register_exception_handlers(app)

# ── CORS 中间件配置 ──────────────────────────────────
# 允许前端跨域请求后端 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 请求日志中间件 ───────────────────────────────────
# 记录每次 API 请求的进入/离开日志（跳过 /docs、/api/health 等路径）
app.add_middleware(RequestLogMiddleware)

# ── 注册路由 ─────────────────────────────────────────
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(scenes_router)
from app.api.training import router as training_router
app.include_router(training_router)
from app.api.detection import router as detection_router
app.include_router(detection_router)
from app.api.history import router as history_router
app.include_router(history_router)
from app.api.stats import router as stats_router
app.include_router(stats_router)


@app.get("/")
def root():
    return {
        "message": "欢迎使用 GLW RSOD Agent Platform",
        "version": "0.1.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
