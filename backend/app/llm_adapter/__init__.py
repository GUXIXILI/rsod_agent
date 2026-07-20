# LLM 适配器：提供通用 OpenAI 兼容接口的自动探测能力
from .probe import (
    find_working_chat_config,
    find_working_embedding_config,
    probe_models,
    test_chat_model,
    test_embedding_model,
)

__all__ = [
    "probe_models",
    "test_chat_model",
    "test_embedding_model",
    "find_working_chat_config",
    "find_working_embedding_config",
]
