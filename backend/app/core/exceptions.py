"""
全局异常处理模块
统一捕获所有异常，返回标准 JSON 格式 {code, message, data}

异常优先级（由具体到通用）：
    1. HTTPException          → 业务异常，保留原始状态码
    2. RequestValidationError → Pydantic 参数校验失败，固定 422
    3. JWTError               → JWT 认证失败，固定 401
    4. Exception              → 兜底未预期异常，固定 500
"""
import traceback
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from jose import JWTError
from app.core.logger import get_logger

# ── 获取当前模块的 logger ──────────────────────────────
logger = get_logger(__name__)


def register_exception_handlers(app):
    """
    注册全局异常处理器到 FastAPI 应用

    所有异常都会被转换为统一的 JSON 响应格式：
        {
            "code": <HTTP 状态码>,
            "message": "<人类可读的错误描述>",
            "data": <附加数据，可能为 null>
        }

    参数：
        app: FastAPI 应用实例
    """

    # ── 1. HTTPException 处理器 ─────────────────────────
    # 处理业务层主动抛出的 HTTP 异常（如 400/401/404/429 等）
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """
        业务异常处理器
        - 400 系列：客户端错误 → 记录 WARNING 日志
        - 500 系列：服务端错误 → 记录 ERROR 日志
        """
        status_code = exc.status_code

        # 根据状态码级别选择日志级别
        if 400 <= status_code < 500:
            # 4xx 客户端错误：WARNING 级别，包含请求路径和具体错误信息
            logger.warning(
                "HTTP 客户端错误 [%d] | 路径: %s %s | 详情: %s",
                status_code,
                request.method,
                request.url.path,
                exc.detail,
            )
        else:
            # 5xx 服务端错误：ERROR 级别
            logger.error(
                "HTTP 服务端错误 [%d] | 路径: %s %s | 详情: %s",
                status_code,
                request.method,
                request.url.path,
                exc.detail,
            )

        # 返回标准 JSON 格式，data 为 null 表示无额外数据
        return JSONResponse(
            status_code=status_code,
            content={
                "code": status_code,
                "message": str(exc.detail) if exc.detail else "请求处理异常",
                "data": None,
            },
        )

    # ── 2. RequestValidationError 处理器 ────────────────
    # 处理 Pydantic 请求参数校验失败（FastAPI 自动将 Pydantic
    # ValidationError 包装为 RequestValidationError）
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """
        请求参数验证失败处理器
        提取每个字段的校验错误信息，组装为列表返回

        示例响应：
            {
                "code": 422,
                "message": "请求参数验证失败",
                "data": [
                    {"field": "username", "message": "field required"},
                    {"field": "password", "message": "field required"}
                ]
            }
        """
        # 提取字段级错误信息
        # exc.errors() 返回一个列表，每个元素包含 loc（字段路径）、msg（错误描述）等
        field_errors = []
        for error in exc.errors():
            # loc 是一个元组，如 ("body", "username")，取最后一个作为字段名
            # 跳过 body/query 等前缀，只保留实际字段名
            field_path = error.get("loc", [])
            field_name = ".".join(str(part) for part in field_path[1:]) if len(field_path) > 1 else "."
            field_errors.append({
                "field": field_name,
                "message": error.get("msg", "校验失败"),
            })

        # 记录 WARNING 日志，包含请求路径和字段错误详情
        logger.warning(
            "请求参数验证失败 | 路径: %s %s | 字段错误: %s",
            request.method,
            request.url.path,
            field_errors,
        )

        return JSONResponse(
            status_code=422,
            content={
                "code": 422,
                "message": "请求参数验证失败",
                "data": field_errors,
            },
        )

    # ── 3. JWTError 处理器 ──────────────────────────────
    # 处理 JWT Token 解析/验证失败（如 Token 过期、签名不匹配、格式错误等）
    @app.exception_handler(JWTError)
    async def jwt_error_handler(request: Request, exc: JWTError):
        """
        JWT 认证失败处理器
        统一返回 401，提示用户重新登录

        注意：此处理器捕获的是未被业务代码捕获的 JWTError，
        例如在 Depends 中直接抛出时会走到这里。
        如果业务代码中已经 catch 了 JWTError 并抛出了
        HTTPException，则会由上面的 http_exception_handler 处理。
        """
        logger.warning(
            "JWT 认证失败 | 路径: %s %s | 原因: %s",
            request.method,
            request.url.path,
            str(exc),
        )

        return JSONResponse(
            status_code=401,
            content={
                "code": 401,
                "message": "认证失败，请重新登录",
                "data": None,
            },
        )

    # ── 4. Exception 兜底处理器 ─────────────────────────
    # 捕获所有未被上述处理器捕获的异常，作为最后的安全网
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """
        未预期异常兜底处理器
        - 记录完整堆栈信息到 ERROR 日志
        - 返回 500 + 通用错误消息，不暴露内部敏感信息
        """
        # 获取完整堆栈跟踪信息
        full_traceback = traceback.format_exc()

        logger.error(
            "未捕获的服务器异常 | 路径: %s %s | 异常类型: %s | 异常信息: %s\n堆栈跟踪:\n%s",
            request.method,
            request.url.path,
            type(exc).__name__,
            str(exc),
            full_traceback,
        )

        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "服务器内部错误，请稍后重试",
                "data": None,
            },
        )