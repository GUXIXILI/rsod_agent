"""
语义检索器

整合文档加载、文本分块、向量化和向量存储的完整检索流程。
提供构建索引、语义检索和重建索引三大核心功能。

检索流程：
    1. 文档加载（DocumentLoader.load_documents）
    2. 文本分块（DocumentLoader.split_documents）
    3. 文本向量化（EmbeddingService.embed_texts）
    4. 向量存储（PgvectorClient.insert_embeddings）
"""

from typing import List, Dict

from app.rag.document_loader import DocumentLoader
from app.rag.embedding import EmbeddingService
from app.vectorstore.pgvector_client import PgvectorClient
from app.core.logger import get_logger

logger = get_logger(__name__)


class SemanticRetriever:
    """
    语义检索器

    提供基于向量相似度的语义检索功能。
    将知识库文档转换为向量索引，支持自然语言查询。
    """

    def __init__(self):
        """初始化语义检索器，创建各子模块实例"""
        self.loader = DocumentLoader()
        self.embedding_service = EmbeddingService()
        self.vectorstore = PgvectorClient()

    def build_index(self, chunk_size: int = 500, chunk_overlap: int = 50) -> Dict:
        """
        构建向量索引（完整流程）

        流程：加载文档 → 文本分块 → 向量化 → 存储到 pgvector

        Args:
            chunk_size: 文本分块大小，默认 500
            chunk_overlap: 文本分块重叠量，默认 50

        Returns:
            Dict: 构建结果统计
                {
                    "status": "success" | "error",
                    "document_count": 文档数,
                    "chunk_count": 分块数,
                    "embedding_count": 向量数,
                    "message": 描述信息
                }
        """
        try:
            # 1. 初始化向量表
            if not self.vectorstore.init_table():
                return {
                    "status": "error",
                    "message": "向量表初始化失败",
                }

            # 2. 加载知识库文档
            documents = self.loader.load_documents()
            if not documents:
                return {
                    "status": "error",
                    "message": "未找到知识库文档，请检查 knowledge_base/ 目录",
                }

            # 3. 文本分块
            chunks = self.loader.split_documents(
                documents,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            if not chunks:
                return {
                    "status": "error",
                    "message": "文档分块结果为空",
                }

            # 4. 提取文本内容和元数据
            texts = [chunk["content"] for chunk in chunks]
            metadatas = [chunk["metadata"] for chunk in chunks]

            # 5. 文本向量化
            embeddings = self.embedding_service.embed_texts(texts)
            if not embeddings:
                return {
                    "status": "error",
                    "message": "文本向量化失败",
                }

            # 6. 存储向量到 pgvector
            inserted = self.vectorstore.insert_embeddings(texts, embeddings, metadatas)

            result = {
                "status": "success",
                "document_count": len(documents),
                "chunk_count": len(chunks),
                "embedding_count": inserted,
                "message": f"向量索引构建完成：{len(documents)} 篇文档，{inserted} 条向量记录",
            }
            logger.info(result["message"])
            return result

        except Exception as e:
            logger.error(f"构建向量索引失败: {e}")
            return {
                "status": "error",
                "message": f"构建向量索引失败: {str(e)}",
            }

    def search(self, query: str, top_k: int = 5) -> Dict:
        """
        语义检索

        对用户查询进行向量化，然后在向量数据库中检索最相似的文档片段。

        流程：查询向量化 → 余弦相似度检索 → 格式化结果

        Args:
            query: 用户查询文本
            top_k: 返回结果数量，默认 5

        Returns:
            Dict: 检索结果
                {
                    "status": "success" | "error",
                    "query": 查询文本,
                    "results": [
                        {
                            "id": 记录ID,
                            "content": 文本内容,
                            "metadata": {"title": "...", "source": "...", "chunk_index": 0},
                            "similarity": 相似度分数
                        },
                        ...
                    ],
                    "count": 结果数量
                }
        """
        try:
            if not query or not query.strip():
                return {
                    "status": "error",
                    "message": "查询文本不能为空",
                }

            # 1. 查询向量化
            query_embedding = self.embedding_service.embed_query(query)
            if not query_embedding:
                return {
                    "status": "error",
                    "message": "查询向量化失败",
                }

            # 2. 向量检索
            results = self.vectorstore.search(query_embedding, top_k=top_k)

            return {
                "status": "success",
                "query": query,
                "results": results,
                "count": len(results),
            }

        except Exception as e:
            logger.error(f"语义检索失败: {e}")
            return {
                "status": "error",
                "message": f"语义检索失败: {str(e)}",
            }

    def rebuild_index(self, chunk_size: int = 500, chunk_overlap: int = 50) -> Dict:
        """
        重建向量索引

        先清空现有向量表，再重新构建索引。
        适用于知识库文档更新后需要刷新索引的场景。

        Args:
            chunk_size: 文本分块大小，默认 500
            chunk_overlap: 文本分块重叠量，默认 50

        Returns:
            Dict: 重建结果统计（同 build_index）
        """
        try:
            # 清空现有向量表
            deleted = self.vectorstore.clear()
            logger.info(f"已清空 {deleted} 条旧向量记录，开始重建索引...")

            # 重新构建索引
            return self.build_index(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        except Exception as e:
            logger.error(f"重建向量索引失败: {e}")
            return {
                "status": "error",
                "message": f"重建向量索引失败: {str(e)}",
            }