"""
登录速率限制模块
基于 Redis 实现登录失败次数限制，防止暴力破解
独立模块 — 不依赖 auth 或 user_service，删除此文件即可移除功能

异常处理说明：
- 当 Redis 不可用时，所有操作降级为“允许登录”，避免阻塞正常认证流程
- 降级情况会被记录到日志，便于运维排查
- 使用 _redis_available 缓存避免每次请求都尝试连接不可用的 Redis
"""
import logging
import redis
import time
from redis.exceptions import RedisError
from app.config.settings import settings

# 模块日志记录器
logger = logging.getLogger(__name__)

# Redis 可用性缓存：避免每次请求都尝试连接不可用的 Redis
# 初始值设为 False，首次请求不会阻塞；每隔 REDIS_CHECK_INTERVAL 秒重试一次
_redis_available = False
_redis_last_check = 0         # 上次检测时间戳
_REDIS_CHECK_INTERVAL = 60    # 检测间隔（秒）


def _is_redis_available() -> bool:
    """
    检测 Redis 是否可用，带缓存机制
    每隔 REDIS_CHECK_INTERVAL 秒重新检测一次
    """
    global _redis_available, _redis_last_check
    now = time.time()

    # 缓存未过期，直接返回缓存结果
    if _redis_available is not None and (now - _redis_last_check) < _REDIS_CHECK_INTERVAL:
        return _redis_available

    # 尝试连接 Redis
    try:
        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        r.ping()  # 真正触发连接
        _redis_available = True
    except Exception:
        _redis_available = False
        logger.warning("Redis 不可用，登录速率限制已降级跳过")

    _redis_last_check = now
    return _redis_available


def _get_redis_client() -> redis.Redis:
    """获取 Redis 连接（仅在 Redis 可用时调用）"""
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
    )


def _build_key(username: str) -> str:
    """构造 Redis key"""
    return f"login_attempts:{username}"


def check_login_rate_limit(username: str) -> tuple:
    """
    检查用户是否被登录锁定
    Args:
        username: 用户名
    Returns:
        (is_locked: bool, remaining_attempts: int)
        - is_locked: True 表示已被锁定，需等待锁定期结束
        - remaining_attempts: 剩余尝试次数（被锁定时为 0）
    """
    # Redis 不可用时直接降级，允许登录
    if not _is_redis_available():
        return (False, settings.LOGIN_MAX_ATTEMPTS)

    try:
        r = _get_redis_client()
        key = _build_key(username)
        attempts = r.get(key)

        if attempts is None:
            # 无失败记录，允许登录
            return (False, settings.LOGIN_MAX_ATTEMPTS)

        attempts = int(attempts)
        if attempts >= settings.LOGIN_MAX_ATTEMPTS:
            return (True, 0)

        remaining = settings.LOGIN_MAX_ATTEMPTS - attempts
        return (False, remaining)
    except RedisError as e:
        # Redis 异常时降级处理：允许登录，避免阻塞正常认证
        logger.warning(f"Redis 连接异常，登录速率限制降级：{e}")
        return (False, settings.LOGIN_MAX_ATTEMPTS)


def record_login_failure(username: str):
    """
    记录一次登录失败
    首次失败时设置 TTL 为锁定时长
    """
    if not _is_redis_available():
        return

    try:
        r = _get_redis_client()
        key = _build_key(username)
        attempts = r.incr(key)

        if attempts == 1:
            # 首次失败，设置过期时间
            r.expire(key, settings.LOGIN_LOCKOUT_MINUTES * 60)

        # 达到上限后，重置 TTL（确保锁定期间不会过期）
        if attempts >= settings.LOGIN_MAX_ATTEMPTS:
            r.expire(key, settings.LOGIN_LOCKOUT_MINUTES * 60)
    except RedisError as e:
        # Redis 异常时跳过记录，不影响认证流程
        logger.warning(f"Redis 连接异常，无法记录登录失败：{e}")


def clear_login_attempts(username: str):
    """清除登录失败记录（登录成功后调用）"""
    if not _is_redis_available():
        return

    try:
        r = _get_redis_client()
        key = _build_key(username)
        r.delete(key)
    except RedisError as e:
        # Redis 异常时跳过清除，不影响认证流程
        logger.warning(f"Redis 连接异常，无法清除登录失败记录：{e}")