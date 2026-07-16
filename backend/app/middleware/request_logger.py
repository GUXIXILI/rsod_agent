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
    """
    API 请求日志中间件。

    记录每个 HTTP 请求的进入（→）和离开（←）日志，
    包含方法、路径、客户端 IP、状态码和耗时。

    跳过文档和健康检查路径，避免日志噪音。
    """

    async def dispatch(self, request, call_next):
        """
        拦截请求并记录请求日志。

        流程：
        1. 跳过不需要记录的路径（文档、健康检查）
        2. 记录请求进入日志（→）
        3. 执行实际请求并计时
        4. 记录请求离开日志（←），包含状态码和耗时
        5. 异常时记录警告日志并重新抛出

        Args:
            request: Starlette Request 对象
            call_next: 下一个中间件或路由处理器

        Returns:
            Response: HTTP 响应对象
        """
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