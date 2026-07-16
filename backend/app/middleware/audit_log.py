"""
操作审计日志中间件

拦截写操作（POST/PUT/DELETE），异步记录到 operation_logs 表。
GET 请求不记录，避免日志噪音。
"""
import json
import re
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.background import BackgroundTask
from jose import JWTError

from app.core.logger import get_logger
from app.core.security import decode_access_token

logger = get_logger(__name__)

# 不记录审计日志的路径前缀
SKIP_PREFIXES = ("/docs", "/redoc", "/openapi.json", "/favicon.ico", "/api/health")

# 路径到模块的映射规则
MODULE_MAP = {
    "auth": "auth",
    "detection": "detection",
    "training": "training",
    "scenes": "detection",
    "chat": "agent",
    "roles": "system",
    "permissions": "system",
    "stats": "system",
    "history": "detection",
}

# HTTP 方法到操作类型的映射
ACTION_MAP = {
    "POST": "create",
    "PUT": "update",
    "DELETE": "delete",
    "PATCH": "update",
}


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    操作审计日志中间件。

    拦截所有写操作（POST/PUT/DELETE/PATCH），异步记录到 operation_logs 表。
    GET 请求不记录，避免日志噪音。

    审计流程：
    1. 只拦截写操作（GET 等读操作直接放行）
    2. 跳过不需要审计的路径（文档、健康检查等）
    3. 从 JWT Token 中提取用户身份
    4. 从请求路径中解析模块、操作类型、目标类型等信息
    5. 读取请求体摘要（脱敏处理密码字段）
    6. 实际请求执行后，通过 BackgroundTask 异步写入数据库
    """

    async def dispatch(self, request: Request, call_next):
        """
        Starlette 中间件入口：拦截请求并记录审计日志。

        对写操作请求，在请求执行前后收集审计信息，通过 BackgroundTask
        异步写入数据库，确保不阻塞响应返回。

        Args:
            request: Starlette Request 对象
            call_next: 下一个中间件或路由处理器

        Returns:
            Response: HTTP 响应对象
        """
        method = request.method

        # 仅拦截写操作
        if method not in ("POST", "PUT", "DELETE", "PATCH"):
            return await call_next(request)

        path = request.url.path

        # 跳过不需要审计的路径
        if any(path.startswith(prefix) for prefix in SKIP_PREFIXES):
            return await call_next(request)

        # 提取审计信息
        user_id, username = self._extract_user(request)
        module, action, target_type, target_id = self._parse_path(path, method)
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")[:500]
        body_summary = await self._read_body_summary(request)

        # 执行实际请求
        response = await call_next(request)

        # 根据响应状态判定操作结果
        status_code = response.status_code
        op_status = "success" if 200 <= status_code < 400 else "failure"

        # 使用 BackgroundTask 异步写入数据库，不阻塞响应
        if response.body_iterator:
            # 将审计任务附加到响应的 background task
            existing_bg = getattr(response, "background", None)

            async def _write_audit():
                if existing_bg:
                    await existing_bg()
                self._save_log(
                    user_id=user_id,
                    username=username,
                    module=module,
                    action=action,
                    target_type=target_type,
                    target_id=target_id,
                    description=f"{method} {path}",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    request_method=method,
                    request_path=path,
                    status=op_status,
                    body_summary=body_summary,
                )

            response.background = BackgroundTask(_write_audit)
        else:
            self._save_log(
                user_id=user_id,
                username=username,
                module=module,
                action=action,
                target_type=target_type,
                target_id=target_id,
                description=f"{method} {path}",
                ip_address=ip_address,
                user_agent=user_agent,
                request_method=method,
                request_path=path,
                status=op_status,
                body_summary=body_summary,
            )

        return response

    def _extract_user(self, request: Request) -> tuple:
        """
        从 Authorization header 中解析 JWT Token 获取用户信息。

        Args:
            request: Starlette Request 对象

        Returns:
            tuple: (user_id, username)，未登录时返回 (None, None)
        """
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return None, None

        token = auth_header[7:]
        try:
            payload = decode_access_token(token)
            user_id_str = payload.get("sub")
            if user_id_str:
                return int(user_id_str), None
        except (JWTError, ValueError):
            pass
        return None, None

    def _parse_path(self, path: str, method: str) -> tuple:
        """
        从请求路径中提取审计元数据。

        解析逻辑：
        - 模块：根据路径第一段映射到业务模块（auth/detection/agent/system）
        - 操作类型：根据 HTTP 方法映射（POST→create, PUT→update, DELETE→delete）
        - 目标类型：取路径第一段作为操作对象类型
        - 目标 ID：取路径中的第一个数字段

        Args:
            path: 请求路径，如 /api/roles/5/permissions
            method: HTTP 方法

        Returns:
            tuple: (module, action, target_type, target_id)
        """
        # 移除 /api/ 前缀
        clean_path = path.replace("/api/", "", 1) if path.startswith("/api/") else path
        parts = clean_path.strip("/").split("/")

        module = "system"
        target_type = None
        target_id = None

        # 解析模块
        if parts:
            first = parts[0]
            module = MODULE_MAP.get(first, "system")
            target_type = first

        # 解析 target_id（路径中的数字段）
        for part in parts[1:]:
            if part.isdigit():
                target_id = part
                break

        action = ACTION_MAP.get(method, method.lower())

        return module, action, target_type, target_id

    async def _read_body_summary(self, request: Request) -> str:
        """
        读取请求体内容并脱敏处理后返回摘要（前 500 字符）。

        脱敏处理：自动隐藏 password、old_password、new_password 字段的值，
        替换为 "***"，防止敏感信息泄露到审计日志中。

        Args:
            request: Starlette Request 对象

        Returns:
            str: 脱敏后的请求体摘要，读取失败时返回空字符串
        """
        try:
            body = await request.body()
            if body:
                text = body.decode("utf-8", errors="replace")
                # 脱敏：隐藏密码字段
                try:
                    data = json.loads(text)
                    for key in ("password", "old_password", "new_password"):
                        if key in data:
                            data[key] = "***"
                    text = json.dumps(data, ensure_ascii=False)
                except (json.JSONDecodeError, TypeError):
                    pass
                return text[:500]
        except Exception:
            pass
        return ""

    def _save_log(self, **kwargs):
        """
        将审计日志写入 operation_logs 表。

        使用独立的数据库会话，写入失败时回滚并记录警告日志，
        确保审计日志记录失败不影响正常业务请求。

        Args:
            **kwargs: 审计日志字段，包括 user_id、module、action 等
        """
        try:
            from app.database.session import SessionLocal
            from app.entity.db_models import OperationLog

            db = SessionLocal()
            try:
                log = OperationLog(
                    user_id=kwargs.get("user_id"),
                    username=kwargs.get("username"),
                    module=kwargs.get("module", "system"),
                    action=kwargs.get("action", "unknown"),
                    target_type=kwargs.get("target_type"),
                    target_id=kwargs.get("target_id"),
                    description=kwargs.get("description"),
                    ip_address=kwargs.get("ip_address"),
                    user_agent=kwargs.get("user_agent"),
                    request_method=kwargs.get("request_method"),
                    request_path=kwargs.get("request_path"),
                    request_body=kwargs.get("body_summary"),
                    status=kwargs.get("status", "success"),
                )
                db.add(log)
                db.commit()
            except Exception as e:
                db.rollback()
                logger.warning(f"审计日志写入失败: {e}")
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"审计日志记录异常: {e}")
