"""
API 请求日志中间件
记录每次请求的方法、路径、客户端 IP、状态码、耗时
"""
import time
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logger import get_logger

logger = get_logger(__name__)

# 跳过的路径（不记录请求日志，避免日志噪音）
SKIP_PATHS = {"/docs", "/redoc", "/openapi.json", "/favicon.ico", "/api/health"}


class RequestLogMiddleware(BaseHTTPMiddleware):
    """API 请求日志中间件"""

    async def dispatch(self, request, call_next):
        # 跳过不需要记录的路径
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"

        # 记录请求进入日志
        logger.info(f"→ {method} {path} | client={client_ip}")

        start_time = time.time()
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            logger.info(f"← {method} {path} | status={response.status_code} | {duration_ms:.1f}ms")
            return response
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.warning(f"← {method} {path} | status=500 | {duration_ms:.1f}ms | error={e}")
            raise