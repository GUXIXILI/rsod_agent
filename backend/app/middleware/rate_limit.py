"""
基于 Redis 的通用 API 限流中间件

使用滑动窗口算法（Redis Sorted Set）实现请求频率限制。
支持按 IP 地址和用户 ID 进行限流，Redis 不可用时自动降级放行。

限流策略：
- 滑动窗口：每个请求的时间戳作为 score 存入 Redis ZSET
- 窗口内超过限制的请求返回 HTTP 429 Too Many Requests
- Redis 不可用时跳过限流，保证服务可用性

配置项（可通过 settings 或环境变量覆盖）：
- RATE_LIMIT_ENABLED: 是否启用限流（默认 True）
- RATE_LIMIT_MAX_REQUESTS: 窗口内最大请求数（默认 100）
- RATE_LIMIT_WINDOW_SECONDS: 滑动窗口大小（秒，默认 60）
- RATE_LIMIT_REDIS_TIMEOUT: Redis 操作超时（秒，默认 2）
"""
import time
from typing import Optional

import redis
from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config.settings import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# ── 限流默认配置 ──────────────────────────────────────────
# 可通过 settings 或环境变量覆盖
RATE_LIMIT_ENABLED = getattr(settings, "RATE_LIMIT_ENABLED", True)
RATE_LIMIT_MAX_REQUESTS = getattr(settings, "RATE_LIMIT_MAX_REQUESTS", 100)
RATE_LIMIT_WINDOW_SECONDS = getattr(settings, "RATE_LIMIT_WINDOW_SECONDS", 60)
RATE_LIMIT_REDIS_TIMEOUT = getattr(settings, "RATE_LIMIT_REDIS_TIMEOUT", 2)

# 不进行限流的路径前缀（健康检查、文档等）
SKIP_PREFIXES = (
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
    "/api/health",
    "/ws",  # WebSocket 连接不适用 HTTP 限流
)

# Redis 连接缓存
_redis_client: Optional[redis.Redis] = None
_redis_available: bool = True
_redis_last_check: float = 0.0
_REDIS_CHECK_INTERVAL: float = 30.0  # Redis 可用性检测间隔（秒）


def _get_redis() -> Optional[redis.Redis]:
    """
    获取 Redis 连接（带缓存和可用性检测）

    连接失败时标记 Redis 不可用，后续请求直接降级放行。
    每隔 REDIS_CHECK_INTERVAL 秒重新尝试连接。

    Returns:
        Redis 客户端实例，不可用时返回 None
    """
    global _redis_client, _redis_available, _redis_last_check

    if not RATE_LIMIT_ENABLED:
        return None

    now = time.time()

    # 缓存未过期时直接返回
    if _redis_client is not None and (now - _redis_last_check) < _REDIS_CHECK_INTERVAL:
        return _redis_client

    # 尝试连接 Redis
    try:
        _redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True,
            socket_connect_timeout=RATE_LIMIT_REDIS_TIMEOUT,
            socket_timeout=RATE_LIMIT_REDIS_TIMEOUT,
        )
        _redis_client.ping()  # 验证连接
        _redis_available = True
        logger.info("Redis 限流连接已建立: %s:%d", settings.REDIS_HOST, settings.REDIS_PORT)
    except Exception as e:
        _redis_client = None
        _redis_available = False
        logger.warning("Redis 不可用，API 限流已降级跳过: %s", e)

    _redis_last_check = now
    return _redis_client


def _build_key(identifier: str) -> str:
    """
    构造 Redis 限流 key

    Args:
        identifier: 限流标识（IP 地址或用户 ID）

    Returns:
        Redis key 字符串
    """
    return f"rate_limit:{identifier}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    基于 Redis 滑动窗口的 API 限流中间件

    限流逻辑：
    1. 获取客户端标识（优先用户 ID，其次 IP 地址）
    2. 使用 Redis ZSET 存储请求时间戳（score = 当前时间戳）
    3. 移除窗口外的旧记录
    4. 统计窗口内请求数，超限返回 429
    5. 未超限则记录当前请求并放行

    降级策略：
    - Redis 不可用时直接放行，不阻塞业务
    - 单次 Redis 操作异常时放行，避免误拦截
    """

    async def dispatch(self, request: Request, call_next):
        # ── 检查是否启用限流 ──────────────────────────────
        if not RATE_LIMIT_ENABLED:
            return await call_next(request)

        # ── 跳过不需要限流的路径 ──────────────────────────
        path = request.url.path
        if any(path.startswith(prefix) for prefix in SKIP_PREFIXES):
            return await call_next(request)

        # ── 获取 Redis 连接 ────────────────────────────────
        r = _get_redis()
        if r is None:
            # Redis 不可用，降级放行
            return await call_next(request)

        # ── 确定限流标识 ──────────────────────────────────
        # 优先使用用户 ID，未登录时使用客户端 IP
        identifier = self._get_identifier(request)

        try:
            # ── 滑动窗口限流 ────────────────────────────────
            key = _build_key(identifier)
            now_ts = time.time()
            window_start = now_ts - RATE_LIMIT_WINDOW_SECONDS

            # 使用 Redis pipeline 保证原子性
            pipe = r.pipeline()
            # 1. 移除窗口外的过期记录
            pipe.zremrangebyscore(key, 0, window_start)
            # 2. 统计窗口内当前请求数
            pipe.zcard(key)
            # 3. 添加当前请求时间戳（使用微秒精度避免冲突）
            pipe.zadd(key, {str(now_ts): now_ts})
            # 4. 设置 key 过期时间（窗口大小的 2 倍，避免残留）
            pipe.expire(key, RATE_LIMIT_WINDOW_SECONDS * 2)

            results = pipe.execute()
            # results[0]: zremrangebyscore 删除数量
            # results[1]: zcard 当前窗口内请求数（添加前）
            current_count = results[1]

            # ── 判断是否超限 ────────────────────────────────
            if current_count >= RATE_LIMIT_MAX_REQUESTS:
                logger.warning(
                    "API 限流触发: identifier=%s, path=%s, count=%d/%d",
                    identifier, path, current_count, RATE_LIMIT_MAX_REQUESTS,
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "code": 429,
                        "message": f"请求过于频繁，请 {RATE_LIMIT_WINDOW_SECONDS} 秒后重试",
                        "data": {
                            "retry_after": RATE_LIMIT_WINDOW_SECONDS,
                            "limit": RATE_LIMIT_MAX_REQUESTS,
                            "window_seconds": RATE_LIMIT_WINDOW_SECONDS,
                        },
                    },
                    headers={
                        "Retry-After": str(RATE_LIMIT_WINDOW_SECONDS),
                        "X-RateLimit-Limit": str(RATE_LIMIT_MAX_REQUESTS),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(now_ts + RATE_LIMIT_WINDOW_SECONDS)),
                    },
                )

            # ── 放行请求 ────────────────────────────────────
            response = await call_next(request)

            # 添加限流信息到响应头
            remaining = max(0, RATE_LIMIT_MAX_REQUESTS - current_count - 1)
            response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_MAX_REQUESTS)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(now_ts + RATE_LIMIT_WINDOW_SECONDS))

            return response

        except RedisError as e:
            # Redis 操作异常，降级放行，避免误拦截
            logger.warning("Redis 限流操作异常，降级放行: %s", e)
            return await call_next(request)
        except Exception as e:
            # 其他异常也降级放行
            logger.exception("API 限流中间件异常: %s", e)
            return await call_next(request)

    @staticmethod
    def _get_identifier(request: Request) -> str:
        """
        获取限流标识

        优先从 JWT token 中提取用户 ID 作为标识，
        未登录时使用客户端 IP 地址。

        Args:
            request: FastAPI 请求对象

        Returns:
            限流标识字符串
        """
        # 尝试从 Authorization header 提取用户 ID
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from app.core.security import decode_access_token
                token = auth_header[7:]
                payload = decode_access_token(token)
                user_id = payload.get("sub")
                if user_id:
                    return f"user:{user_id}"
            except Exception:
                pass  # Token 解析失败，回退到 IP

        # 回退到客户端 IP
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"