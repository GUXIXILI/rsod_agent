"""
健康检查 API 路由
提供基础健康检查和详细依赖检查两个端点
"""
from fastapi import APIRouter
from app.config.settings import settings
from app.core.logger import get_logger

# 创建健康检查路由器，统一前缀 /api/health
router = APIRouter(prefix="/api/health", tags=["健康检查"])

# 使用模块级 logger 记录健康检查中的详细异常，便于排查问题
logger = get_logger(__name__)


@router.get("")
def health_check():
    """
    基础健康检查（Liveness Probe）
    用于 Kubernetes 或负载均衡器检测服务是否存活
    不依赖任何外部服务，仅确认进程本身正常运行
    """
    return {
        "code": 200,
        "message": "服务运行正常",
        "data": {
            "status": "healthy",
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
        },
    }


@router.get("/detail")
def health_detail():
    """
    详细健康检查（Readiness Probe）
    逐一检查 PostgreSQL、Redis、MinIO 的连接状态
    任一依赖不可用时标记为 unhealthy，但不抛出异常，保证接口始终返回结果
    """
    # ── 检查 PostgreSQL ──────────────────────────────────
    # 使用 raw SQL 执行 SELECT 1 来验证数据库连接是否正常
    pg_status = "healthy"
    pg_message = "数据库连接正常"
    try:
        from sqlalchemy import text
        from app.database.session import SessionLocal

        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
    except Exception as e:
        pg_status = "unhealthy"
        # 对外隐藏详细异常信息，避免泄露数据库主机、端口、用户名等敏感配置
        pg_message = "数据库连接失败"
        logger.warning(f"PostgreSQL 健康检查失败: {e}")

    # ── 检查 Redis ───────────────────────────────────────
    # 使用 PING 命令验证 Redis 连接是否正常
    redis_status = "healthy"
    redis_message = "Redis 连接正常"
    try:
        import redis

        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        r.ping()
    except Exception as e:
        redis_status = "unhealthy"
        # 对外隐藏详细异常信息，避免泄露 Redis 主机、端口等敏感配置
        redis_message = "Redis 连接失败"
        logger.warning(f"Redis 健康检查失败: {e}")

    # ── 检查 MinIO ───────────────────────────────────────
    # 实例化 MinIOClient 验证 MinIO 连接是否正常
    minio_status = "healthy"
    minio_message = "MinIO 连接正常"
    try:
        from app.storage.minio_client import MinIOClient

        MinIOClient()
    except Exception as e:
        minio_status = "unhealthy"
        # 对外隐藏详细异常信息，避免泄露 MinIO 端点、凭证等敏感配置
        minio_message = "MinIO 连接失败"
        logger.warning(f"MinIO 健康检查失败: {e}")

    # ── 汇总结果 ─────────────────────────────────────────
    all_healthy = (
        pg_status == "healthy"
        and redis_status == "healthy"
        and minio_status == "healthy"
    )

    return {
        "code": 200,
        "message": "详细健康检查完成",
        "data": {
            "status": "healthy" if all_healthy else "unhealthy",
            "dependencies": {
                "postgresql": {"status": pg_status, "message": pg_message},
                "redis": {"status": redis_status, "message": redis_message},
                "minio": {"status": minio_status, "message": minio_message},
            },
        },
    }