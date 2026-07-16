"""
知识库管理 API 路由

提供知识库索引构建、语义检索和统计查询功能。
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.rag.retriever import SemanticRetriever
from app.vectorstore.pgvector_client import PgvectorClient
from app.api.auth import get_current_user
from app.core.logger import get_logger

# 创建知识库路由器，统一前缀 /api/knowledge
router = APIRouter(prefix="/api/knowledge", tags=["知识库管理"])

logger = get_logger(__name__)


# ── 响应模型 ──────────────────────────────────────────


class BuildResponse(BaseModel):
    """索引构建响应模型"""
    status: str = Field(..., description="构建状态：success 或 error")
    document_count: int = Field(default=0, description="加载的文档数量")
    chunk_count: int = Field(default=0, description="分块数量")
    embedding_count: int = Field(default=0, description="向量化数量")
    message: str = Field(default="", description="状态描述信息")


class SearchResult(BaseModel):
    """单条检索结果模型"""
    id: int = Field(..., description="记录 ID")
    content: str = Field(..., description="文本内容")
    metadata: dict = Field(default_factory=dict, description="元数据（标题、来源等）")
    similarity: float = Field(..., description="余弦相似度分数")


class SearchResponse(BaseModel):
    """检索响应模型"""
    status: str = Field(..., description="检索状态：success 或 error")
    query: str = Field(default="", description="查询文本")
    results: list = Field(default_factory=list, description="检索结果列表")
    count: int = Field(default=0, description="结果数量")
    message: str = Field(default="", description="状态描述信息")


class StatsResponse(BaseModel):
    """知识库统计响应模型"""
    status: str = Field(..., description="状态")
    total_records: int = Field(default=0, description="向量记录总数")


# ── API 路由 ──────────────────────────────────────────


@router.post("/build", response_model=BuildResponse)
async def build_knowledge_index(current_user=Depends(get_current_user)):
    """
    构建/重建知识库向量索引

    完整流程：加载 knowledge_base/ 目录下的 .md 文档
    → 文本分块 → 向量化 → 存储到 pgvector

    如果已有索引，会先清空再重建。
    """
    logger.info("收到知识库索引构建请求（用户: %s）", getattr(current_user, "username", "unknown"))
    retriever = SemanticRetriever()
    result = retriever.rebuild_index()
    return BuildResponse(**result)


@router.get("/search", response_model=SearchResponse)
async def search_knowledge(
    q: str = Query(..., description="查询文本（自然语言问题）"),
    top_k: int = Query(default=5, ge=1, le=20, description="返回结果数量，1-20"),
    current_user=Depends(get_current_user),
):
    """
    语义检索知识库

    对用户查询进行向量化后，在知识库向量索引中检索最相似的文档片段。

    Args:
        q: 查询文本，支持自然语言问题
        top_k: 返回结果数量，默认 5，范围 1-20
    """
    logger.info(f"收到知识库检索请求: query='{q[:50]}...', top_k={top_k}")

    if not q.strip():
        return SearchResponse(
            status="error",
            message="查询文本不能为空",
        )

    retriever = SemanticRetriever()
    result = retriever.search(query=q, top_k=top_k)

    return SearchResponse(**result)


@router.get("/stats", response_model=StatsResponse)
async def knowledge_stats(current_user=Depends(get_current_user)):
    """
    获取知识库统计信息

    返回当前向量存储中的记录总数。
    """
    logger.info("收到知识库统计请求")
    vectorstore = PgvectorClient()
    total = vectorstore.count()
    return StatsResponse(
        status="success",
        total_records=total,
    )