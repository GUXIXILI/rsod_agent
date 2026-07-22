from __future__ import annotations

import logging
from typing import Any

import openai
from openai import OpenAI
from openai import (
    APIStatusError,
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    PermissionDeniedError,
)

logger = logging.getLogger(__name__)


# 辅助函数：统一格式化异常信息，避免暴露敏感内容
def _format_error(err: Exception) -> str:
    if isinstance(err, APIStatusError):
        message = getattr(err, "message", str(err))
        return f"HTTP {err.status_code}: {message}"
    if isinstance(err, APITimeoutError):
        return f"请求超时: {err}"
    if isinstance(err, APIConnectionError):
        return f"连接失败: {err}"
    return str(err)


# 辅助函数：判断是否为 401/403 等鉴权错误
def _is_auth_error(err: Exception) -> bool:
    if isinstance(err, (AuthenticationError, PermissionDeniedError)):
        return True
    if isinstance(err, APIStatusError) and err.status_code in (401, 403):
        return True
    return False


# 辅助函数：创建 OpenAI 兼容客户端
def _make_client(base_url: str, api_key: str, timeout: int) -> OpenAI:
    return OpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
    )


def probe_models(base_url: str, api_key: str) -> list[str]:
    """
    调用 {base_url}/models 获取模型列表，返回模型 ID 列表。
    若失败（包含网络异常、鉴权失败等）则返回空列表。
    """
    models, _, _ = _fetch_models(base_url, api_key)
    return models


def _fetch_models(
    base_url: str, api_key: str, timeout: int = 10
) -> tuple[list[str], str, bool]:
    """
    内部函数：获取模型列表，同时返回错误信息和是否鉴权失败。
    返回值: (模型ID列表, 错误信息, 是否鉴权失败)
    """
    try:
        client = _make_client(base_url, api_key, timeout)
        # OpenAI 兼容接口的 /models 端点
        response = client.models.list()
        ids = [model.id for model in response.data if getattr(model, "id", None)]
        return ids, "", False
    except Exception as err:  # noqa: BLE001
        error_msg = _format_error(err)
        logger.debug("获取模型列表失败: %s", error_msg)
        return [], error_msg, _is_auth_error(err)


def test_chat_model(
    base_url: str, api_key: str, model: str, timeout: int = 10
) -> tuple[bool, str]:
    """
    使用 OpenAI 兼容接口发送极简 chat.completions 请求，
    返回 (是否成功, 错误信息或模型回复内容)。
    """
    try:
        client = _make_client(base_url, api_key, timeout)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=5,
            timeout=timeout,
        )
        content = ""
        if response.choices and response.choices[0].message:
            content = response.choices[0].message.content or ""
        return True, content
    except Exception as err:  # noqa: BLE001
        return False, _format_error(err)


def test_embedding_model(
    base_url: str, api_key: str, model: str, timeout: int = 10
) -> tuple[bool, str]:
    """
    使用 OpenAI 兼容接口发送 embeddings 请求，
    返回 (是否成功, 错误信息或向量维度字符串)。
    """
    try:
        client = _make_client(base_url, api_key, timeout)
        response = client.embeddings.create(
            model=model,
            input="test",
            timeout=timeout,
        )
        dimension = 0
        if response.data and response.data[0].embedding:
            dimension = len(response.data[0].embedding)
        return True, str(dimension)
    except Exception as err:  # noqa: BLE001
        return False, _format_error(err)


def _try_chat_model(
    base_url: str, api_key: str, model: str, timeout: int
) -> tuple[bool, str, bool]:
    """
    内部函数：尝试调用 Chat 模型。
    返回值: (是否成功, 结果/错误信息, 是否鉴权失败)
    """
    try:
        client = _make_client(base_url, api_key, timeout)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=5,
            timeout=timeout,
        )
        content = ""
        if response.choices and response.choices[0].message:
            content = response.choices[0].message.content or ""
        return True, content, False
    except Exception as err:  # noqa: BLE001
        return False, _format_error(err), _is_auth_error(err)


def _try_embedding_model(
    base_url: str, api_key: str, model: str, timeout: int
) -> tuple[bool, str, bool]:
    """
    内部函数：尝试调用 Embedding 模型。
    返回值: (是否成功, 结果/错误信息, 是否鉴权失败)
    """
    try:
        client = _make_client(base_url, api_key, timeout)
        response = client.embeddings.create(
            model=model,
            input="test",
            timeout=timeout,
        )
        dimension = 0
        if response.data and response.data[0].embedding:
            dimension = len(response.data[0].embedding)
        return True, str(dimension), False
    except Exception as err:  # noqa: BLE001
        return False, _format_error(err), _is_auth_error(err)


def _build_failure_result(
    *, tested_model: str, success: bool, error: str
) -> dict[str, Any]:
    """统一构造配置探测结果字典。"""
    return {"model": tested_model, "success": success, "error": error}


def find_working_chat_config(
    base_url: str,
    api_key: str,
    preferred_models: list[str] | None = None,
    timeout: int = 10,
) -> dict[str, Any]:
    """
    优先尝试 preferred_models 中的 Chat 模型；若都失败，
    则从 /models 获取模型列表继续探测。
    对于 401/403 等鉴权错误会立即快速失败，并明确提示 API key 无效。
    """
    preferred = list(preferred_models or [])

    # 第一步：优先尝试用户指定的模型
    for model in preferred:
        ok, msg, auth_failed = _try_chat_model(base_url, api_key, model, timeout)
        if auth_failed:
            return _build_failure_result(
                tested_model=model,
                success=False,
                error=f"API key 无效（{msg}）",
            )
        if ok:
            return _build_failure_result(tested_model=model, success=True, error=msg)

    # 第二步：获取远端模型列表继续探测
    remote_models, list_error, list_auth_failed = _fetch_models(base_url, api_key, timeout)
    if list_auth_failed:
        return _build_failure_result(
            tested_model="",
            success=False,
            error=f"API key 无效（{list_error}）",
        )

    # 去重，避免重复测试 preferred_models 中已经出现过的模型
    tested = set(preferred)
    candidates = [m for m in remote_models if m not in tested]

    for model in candidates:
        ok, msg, auth_failed = _try_chat_model(base_url, api_key, model, timeout)
        if auth_failed:
            return _build_failure_result(
                tested_model=model,
                success=False,
                error=f"API key 无效（{msg}）",
            )
        if ok:
            return _build_failure_result(tested_model=model, success=True, error=msg)

    # 全部失败，组装友好的错误信息
    if list_error:
        error = f"无法获取模型列表: {list_error}"
    elif not remote_models:
        error = "模型列表为空，请检查 base_url 与 API key 是否正确"
    else:
        error = "所有候选 Chat 模型均调用失败"
    return _build_failure_result(tested_model="", success=False, error=error)


def find_working_embedding_config(
    base_url: str,
    api_key: str,
    preferred_models: list[str] | None = None,
    timeout: int = 10,
) -> dict[str, Any]:
    """
    优先尝试 preferred_models 中的 Embedding 模型；若都失败，
    则从 /models 获取模型列表继续探测。
    对于 401/403 等鉴权错误会立即快速失败，并明确提示 API key 无效。
    """
    preferred = list(preferred_models or [])

    # 第一步：优先尝试用户指定的模型
    for model in preferred:
        ok, msg, auth_failed = _try_embedding_model(base_url, api_key, model, timeout)
        if auth_failed:
            return _build_failure_result(
                tested_model=model,
                success=False,
                error=f"API key 无效（{msg}）",
            )
        if ok:
            return _build_failure_result(tested_model=model, success=True, error=msg)

    # 第二步：获取远端模型列表继续探测
    # AQUA 平台（api.ltzy.top）对话模型支持 embedding，遍历远程模型寻找可用者
    remote_models, list_error, list_auth_failed = _fetch_models(base_url, api_key, timeout)
    if list_auth_failed:
        return _build_failure_result(
            tested_model="",
            success=False,
            error=f"API key 无效（{list_error}）",
        )

    # 去重，避免重复测试 preferred_models 中已经出现过的模型
    tested = set(preferred)
    candidates = [m for m in remote_models if m not in tested]

    for model in candidates:
        ok, msg, auth_failed = _try_embedding_model(base_url, api_key, model, timeout)
        if auth_failed:
            return _build_failure_result(
                tested_model=model,
                success=False,
                error=f"API key 无效（{msg}）",
            )
        if ok:
            return _build_failure_result(tested_model=model, success=True, error=msg)

    # 全部失败，组装友好的错误信息
    if list_error:
        error = f"无法获取模型列表: {list_error}"
    elif not remote_models:
        error = "模型列表为空，请检查 base_url 与 API key 是否正确"
    else:
        error = "所有候选 Embedding 模型均调用失败"
    return _build_failure_result(tested_model="", success=False, error=error)
