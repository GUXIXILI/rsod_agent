"""
文本向量化服务

提供文本向量化功能，支持两种模式：
- LLM_STUB_MODE=true：使用 hash-based 确定性随机向量（占位模式，不发起真实 API 调用）
- LLM_STUB_MODE=false：使用 OpenAI text-embedding-3-small 或通义千问 text-embedding-v3 模型

同一文本在 hash-based 模式下始终生成相同的向量，保证确定性。
"""

import hashlib
import struct
from typing import List

from app.config.settings import settings


class EmbeddingService:
    """
    文本向量化服务

    支持批量文本向量化和单条查询向量化。
    在 LLM_STUB_MODE 下使用 hash-based 随机向量，
    在正常模式下调用远程 Embedding API。
    """

    # 默认向量维度（text-embedding-3-small 为 1536，text-embedding-v3 为 1024）
    # 占位模式下使用 1024 维
    EMBEDDING_DIM = 1024

    def __init__(self):
        """初始化 Embedding 服务，根据配置选择模式"""
        self.stub_mode = settings.LLM_STUB_MODE
        self.model = getattr(settings, "EMBEDDING_MODEL", "text-embedding-3-small")

    def _hash_to_vector(self, text: str) -> List[float]:
        """
        使用 SHA-256 哈希将文本转换为确定性向量（占位模式）

        原理：
        1. 对文本进行 SHA-256 哈希，得到 32 字节的哈希值
        2. 将哈希值循环扩展为 1024 维向量（32 × 32 = 1024）
        3. 将每个字节映射到 [-1, 1] 区间并归一化

        同一文本始终生成相同的向量，保证确定性。

        Args:
            text: 输入文本

        Returns:
            List[float]: 1024 维归一化向量
        """
        # SHA-256 哈希，得到 32 字节
        hash_bytes = hashlib.sha256(text.encode("utf-8")).digest()

        # 将 32 字节循环扩展为 1024 维（32 × 32 = 1024）
        vector = []
        for i in range(self.EMBEDDING_DIM):
            byte_val = hash_bytes[i % 32]
            # 将字节值 (0-255) 映射到 [-1, 1]
            normalized = (byte_val / 127.5) - 1.0
            vector.append(normalized)

        # L2 归一化
        norm = sum(v * v for v in vector) ** 0.5
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector

    def _embed_via_openai(self, texts: List[str]) -> List[List[float]]:
        """
        通过 OpenAI API 进行文本向量化

        Args:
            texts: 文本列表

        Returns:
            List[List[float]]: 向量列表
        """
        import openai

        api_key = getattr(settings, "OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 未配置，无法调用 OpenAI Embedding API")

        client = openai.OpenAI(api_key=api_key)
        response = client.embeddings.create(
            model=self.model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def _embed_via_qwen(self, texts: List[str]) -> List[List[float]]:
        """
        通过通义千问 API 进行文本向量化（使用 OpenAI 兼容 SDK 批量请求）

        优先使用 OpenAI SDK 调用 DashScope 兼容接口，每批最多 20 条文本。
        如果 openai 库不可用，自动降级为逐条 HTTP 请求方式。

        Args:
            texts: 文本列表

        Returns:
            List[List[float]]: 向量列表
        """
        api_key = getattr(settings, "EMBEDDING_API_KEY", "")
        if not api_key:
            raise ValueError("EMBEDDING_API_KEY 未配置，无法调用 Embedding API")

        base_url = getattr(settings, "EMBEDDING_BASE_URL", "")
        # 使用独立的 Embedding API 配置（与对话 LLM 分离）

        # 尝试使用 OpenAI 兼容 SDK 批量请求
        try:
            from openai import OpenAI
        except ImportError:
            # 降级：SDK 不可用时使用原有的逐条 HTTP 请求
            return self._embed_via_qwen_http(texts)

        if not hasattr(self, '_qwen_client') or self._qwen_client is None:
            self._qwen_client = OpenAI(api_key=api_key, base_url=base_url)

        embeddings = []
        batch_size = 20
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = self._qwen_client.embeddings.create(
                model=self.model,
                input=batch,
            )
            embeddings.extend([item.embedding for item in response.data])

        return embeddings

    def _embed_via_qwen_http(self, texts: List[str]) -> List[List[float]]:
        """
        降级方案：逐条 HTTP 请求通义千问 Embedding API

        仅在 openai SDK 不可用时使用。

        Args:
            texts: 文本列表

        Returns:
            List[List[float]]: 向量列表
        """
        import requests

        api_key = getattr(settings, "EMBEDDING_API_KEY", "")
        url = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        embeddings = []
        for text in texts:
            payload = {
                "model": self.model,
                "input": {"texts": [text]},
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            embeddings.append(data["output"]["embeddings"][0]["embedding"])

        return embeddings

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        批量文本向量化

        根据 LLM_STUB_MODE 配置选择向量化方式：
        - stub 模式：使用 hash-based 确定性随机向量
        - 正常模式：根据 EMBEDDING_MODEL 选择 OpenAI 或通义千问 API

        Args:
            texts: 待向量化的文本列表

        Returns:
            List[List[float]]: 向量列表，每个向量为 float 列表
        """
        if not texts:
            return []

        if self.stub_mode:
            # 占位模式：使用 hash-based 确定性随机向量
            return [self._hash_to_vector(text) for text in texts]

        # 正常模式：调用远程 Embedding API
        # 当前项目复用 QWEN 配置（BASE_URL + API_KEY）调用所有 Embedding 模型，
        # 包括 baai/bge-m3、nvidia/nv-embed-v1 等，统一走 OpenAI 兼容接口。
        return self._embed_via_qwen(texts)

    def embed_query(self, query: str) -> List[float]:
        """
        单条查询文本向量化

        对用户输入的查询语句进行向量化，用于语义检索。

        Args:
            query: 查询文本

        Returns:
            List[float]: 查询文本的向量表示
        """
        results = self.embed_texts([query])
        return results[0] if results else []