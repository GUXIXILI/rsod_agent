"""
Pgvector 向量存储客户端

基于 PostgreSQL pgvector 扩展的向量存储与检索模块。
支持创建向量表、批量插入向量、余弦相似度检索等功能。

pgvector 扩展需在 PostgreSQL 中预先安装：
    CREATE EXTENSION IF NOT EXISTS vector;

表结构：
    knowledge_embeddings (
        id          SERIAL PRIMARY KEY,
        content     TEXT NOT NULL,          -- 原始文本内容
        embedding   vector(1024) NOT NULL,  -- 向量（1024 维）
        metadata    JSONB DEFAULT '{}',     -- 元数据（标题、来源、分块索引等）
        created_at  TIMESTAMP DEFAULT NOW()
    )
"""

import json
from typing import List, Dict, Optional

from sqlalchemy import text
from app.database.session import SessionLocal
from app.core.logger import get_logger

logger = get_logger(__name__)


class PgvectorClient:
    """
    Pgvector 向量存储客户端

    封装基于 PostgreSQL pgvector 扩展的向量存储操作，
    包括建表、插入、检索、统计和清理。
    """

    # 向量维度，需与 EmbeddingService 保持一致
    VECTOR_DIM = 1024
    # 表名
    TABLE_NAME = "knowledge_embeddings"

    def __init__(self):
        """初始化 Pgvector 客户端"""
        pass

    def _get_db(self):
        """
        获取数据库会话

        Returns:
            Session: SQLAlchemy 数据库会话
        """
        db = SessionLocal()
        try:
            return db
        except Exception:
            db.close()
            raise

    def init_table(self) -> bool:
        """
        初始化 knowledge_embeddings 表

        步骤：
        1. 启用 pgvector 扩展（如果尚未启用）
        2. 创建 knowledge_embeddings 表（如果不存在）

        Returns:
            bool: 初始化是否成功
        """
        db = self._get_db()
        try:
            # 启用 pgvector 扩展
            db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

            # 创建向量表
            create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
                    id          SERIAL PRIMARY KEY,
                    content     TEXT NOT NULL,
                    embedding   vector({self.VECTOR_DIM}) NOT NULL,
                    metadata    JSONB DEFAULT '{{}}',
                    created_at  TIMESTAMP DEFAULT NOW()
                )
            """
            db.execute(text(create_table_sql))

            # 创建索引以加速检索（IVFFlat 索引，适合近似最近邻搜索）
            create_index_sql = f"""
                CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME}_embedding
                ON {self.TABLE_NAME}
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """
            db.execute(text(create_index_sql))

            db.commit()
            logger.info(f"向量表 {self.TABLE_NAME} 初始化完成")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"向量表初始化失败: {e}")
            return False
        finally:
            db.close()

    def insert_embeddings(
        self,
        contents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict] = None,
    ) -> int:
        """
        批量插入向量

        将文本内容、向量和元数据批量插入 knowledge_embeddings 表。

        Args:
            contents: 文本内容列表
            embeddings: 向量列表，每个向量为 float 列表
            metadatas: 元数据字典列表，与 contents 一一对应

        Returns:
            int: 成功插入的记录数
        """
        if not contents or not embeddings:
            return 0

        if metadatas is None:
            metadatas = [{}] * len(contents)

        db = self._get_db()
        inserted = 0
        try:
            for content, embedding, metadata in zip(contents, embeddings, metadatas):
                # 将向量格式化为 pgvector 兼容的字符串格式 '[1.0, 2.0, ...]'
                vector_str = "[" + ",".join(str(v) for v in embedding) + "]"
                metadata_json = json.dumps(metadata, ensure_ascii=False)

                insert_sql = f"""
                    INSERT INTO {self.TABLE_NAME} (content, embedding, metadata)
                    VALUES (:content, :embedding, :metadata)
                """
                db.execute(
                    text(insert_sql),
                    {
                        "content": content,
                        "embedding": vector_str,
                        "metadata": metadata_json,
                    },
                )
                inserted += 1

            db.commit()
            logger.info(f"成功插入 {inserted} 条向量记录")
        except Exception as e:
            db.rollback()
            logger.error(f"插入向量失败: {e}")
        finally:
            db.close()

        return inserted

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[Dict]:
        """
        余弦相似度检索

        使用 pgvector 的 <=> 操作符（余弦距离）进行相似度检索，
        返回与查询向量最相似的 top_k 条记录。

        余弦距离转换为余弦相似度：similarity = 1 - cosine_distance

        Args:
            query_embedding: 查询向量
            top_k: 返回结果数量，默认 5

        Returns:
            List[Dict]: 检索结果列表，每条包含 id、content、metadata、similarity
        """
        if not query_embedding:
            return []

        db = self._get_db()
        results = []
        try:
            vector_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

            # 使用 <=> 操作符计算余弦距离，1 - 距离 = 相似度
            search_sql = f"""
                SELECT
                    id,
                    content,
                    metadata,
                    1 - (embedding <=> :query_vector) AS similarity
                FROM {self.TABLE_NAME}
                ORDER BY embedding <=> :query_vector
                LIMIT :top_k
            """
            rows = db.execute(
                text(search_sql),
                {"query_vector": vector_str, "top_k": top_k},
            ).fetchall()

            for row in rows:
                results.append({
                    "id": row[0],
                    "content": row[1],
                    "metadata": row[2] if isinstance(row[2], dict) else json.loads(row[2]) if row[2] else {},
                    "similarity": round(float(row[3]), 4),
                })

        except Exception as e:
            logger.error(f"向量检索失败: {e}")
        finally:
            db.close()

        return results

    def count(self) -> int:
        """
        统计向量表中的记录数

        Returns:
            int: 记录总数
        """
        db = self._get_db()
        try:
            result = db.execute(text(f"SELECT COUNT(*) FROM {self.TABLE_NAME}")).scalar()
            return result or 0
        except Exception as e:
            logger.error(f"统计向量记录数失败: {e}")
            return 0
        finally:
            db.close()

    def clear(self) -> int:
        """
        清空向量表

        删除 knowledge_embeddings 表中的所有记录。

        Returns:
            int: 被删除的记录数
        """
        db = self._get_db()
        try:
            result = db.execute(text(f"DELETE FROM {self.TABLE_NAME}")).rowcount
            db.commit()
            logger.info(f"已清空向量表，删除 {result} 条记录")
            return result
        except Exception as e:
            db.rollback()
            logger.error(f"清空向量表失败: {e}")
            return 0
        finally:
            db.close()