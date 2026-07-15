"""
基于 Redis 的对话记忆管理

提供对话历史记录的存储和读取功能。
支持多用户多会话的对话记忆管理，Redis 不可用时自动降级到内存缓存。

Redis Key 格式：chat:session:{user_id}:{session_id}
存储结构：JSON 列表，每条消息包含 role、content、timestamp
"""

import json
import time
from typing import List, Dict, Optional
from collections import defaultdict

import redis

from app.config.settings import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# Redis 连接超时配置（秒）
REDIS_CONNECT_TIMEOUT = 3
REDIS_SOCKET_TIMEOUT = 3

# 会话消息 TTL（秒），默认 1 小时
SESSION_TTL = 3600

# 最大加载历史消息数
MAX_HISTORY_MESSAGES = 20


class ConversationMemory:
    """
    对话记忆管理器

    基于 Redis 的对话记忆存储，支持：
    - 多用户多会话隔离
    - 消息自动过期（TTL 3600 秒）
    - Redis 不可用时降级到内存缓存
    - 限制历史消息数量（最多 20 条）
    """

    def __init__(self):
        """
        初始化对话记忆管理器

        尝试连接 Redis，如果连接失败则降级到内存缓存模式。
        """
        self._redis: Optional[redis.Redis] = None
        self._redis_available = False

        # 内存降级缓存：{key: List[Dict]}
        self._memory_cache: Dict[str, List[Dict]] = defaultdict(list)

        # 尝试连接 Redis
        try:
            self._redis = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                socket_connect_timeout=REDIS_CONNECT_TIMEOUT,
                socket_timeout=REDIS_SOCKET_TIMEOUT,
                decode_responses=True,
            )
            self._redis.ping()
            self._redis_available = True
            logger.info("Redis 连接成功，对话记忆将使用 Redis 存储")
        except Exception as e:
            self._redis_available = False
            logger.warning(f"Redis 连接失败，对话记忆将降级到内存缓存: {e}")

    def _build_key(self, user_id: str, session_id: str) -> str:
        """
        构建 Redis Key

        Args:
            user_id: 用户 ID
            session_id: 会话 ID

        Returns:
            str: Redis Key，格式为 chat:session:{user_id}:{session_id}
        """
        return f"chat:session:{user_id}:{session_id}"

    def save_message(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
    ) -> bool:
        """
        保存一条对话消息

        将消息追加到会话历史中，并设置 TTL 过期时间。

        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            role: 消息角色（user / assistant / system）
            content: 消息内容

        Returns:
            bool: 保存是否成功
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
        }
        message_json = json.dumps(message, ensure_ascii=False)

        if self._redis_available:
            try:
                key = self._build_key(user_id, session_id)
                pipe = self._redis.pipeline()
                # 将消息追加到列表右侧
                pipe.rpush(key, message_json)
                # 限制历史消息数量（保留最近 100 条原始记录，加载时截取 20 条）
                pipe.ltrim(key, -100, -1)
                # 设置 TTL
                pipe.expire(key, SESSION_TTL)
                pipe.execute()
                return True
            except Exception as e:
                logger.warning(f"Redis 保存消息失败，降级到内存缓存: {e}")
                self._redis_available = False

        # 降级到内存缓存
        key = self._build_key(user_id, session_id)
        self._memory_cache[key].append(message)
        # 限制缓存大小
        if len(self._memory_cache[key]) > 100:
            self._memory_cache[key] = self._memory_cache[key][-100:]
        return True

    def load_history(
        self,
        user_id: str,
        session_id: str,
        limit: int = MAX_HISTORY_MESSAGES,
    ) -> List[Dict[str, str]]:
        """
        加载会话历史消息

        从 Redis 或内存缓存中加载指定会话的最近 N 条消息。

        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            limit: 最多加载的消息数，默认 20

        Returns:
            List[Dict]: 消息列表，每条包含 role 和 content 字段
                格式：[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
        """
        messages = []

        if self._redis_available:
            try:
                key = self._build_key(user_id, session_id)
                # 获取列表最后 limit 条记录
                raw_messages = self._redis.lrange(key, -limit, -1)
                for raw in raw_messages:
                    try:
                        msg = json.loads(raw)
                        messages.append({
                            "role": msg.get("role", "user"),
                            "content": msg.get("content", ""),
                        })
                    except json.JSONDecodeError:
                        continue
                return messages
            except Exception as e:
                logger.warning(f"Redis 加载历史失败，降级到内存缓存: {e}")
                self._redis_available = False

        # 降级到内存缓存
        key = self._build_key(user_id, session_id)
        cached = self._memory_cache.get(key, [])
        for msg in cached[-limit:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

        return messages

    def get_sessions(self, user_id: str) -> List[str]:
        """
        获取用户的所有会话 ID 列表

        通过扫描 Redis key 或内存缓存获取指定用户的所有会话。

        Args:
            user_id: 用户 ID

        Returns:
            List[str]: 会话 ID 列表
        """
        sessions = set()

        if self._redis_available:
            try:
                pattern = f"chat:session:{user_id}:*"
                # 使用 SCAN 遍历 key，避免 KEYS 阻塞 Redis
                cursor = 0
                while True:
                    cursor, keys = self._redis.scan(
                        cursor=cursor, match=pattern, count=100
                    )
                    for key in keys:
                        # 从 key 中提取 session_id
                        # key 格式: chat:session:{user_id}:{session_id}
                        parts = key.split(":", 4)
                        if len(parts) >= 4:
                            sessions.add(parts[3])
                    if cursor == 0:
                        break
                return list(sessions)
            except Exception as e:
                logger.warning(f"Redis 获取会话列表失败，降级到内存缓存: {e}")
                self._redis_available = False

        # 降级到内存缓存
        prefix = f"chat:session:{user_id}:"
        for key in self._memory_cache:
            if key.startswith(prefix):
                session_id = key[len(prefix):]
                if self._memory_cache[key]:  # 只返回有消息的会话
                    sessions.add(session_id)

        return list(sessions)

    def clear_session(self, user_id: str, session_id: str) -> bool:
        """
        清空指定会话的所有消息

        Args:
            user_id: 用户 ID
            session_id: 会话 ID

        Returns:
            bool: 清空是否成功
        """
        if self._redis_available:
            try:
                key = self._build_key(user_id, session_id)
                self._redis.delete(key)
                return True
            except Exception as e:
                logger.warning(f"Redis 清空会话失败，降级到内存缓存: {e}")
                self._redis_available = False

        # 降级到内存缓存
        key = self._build_key(user_id, session_id)
        if key in self._memory_cache:
            del self._memory_cache[key]
        return True

    @property
    def is_available(self) -> bool:
        """
        检查 Redis 是否可用

        Returns:
            bool: Redis 是否可用
        """
        return self._redis_available