"""
知识检索工具封装模块

封装 RAG 知识检索工具 search_knowledge，调用 knowledge_retriever.search()
进行火灾烟雾检测相关知识的语义检索。

在 LLM_STUB_MODE=true 时，knowledge_retriever 使用占位实现，
返回模拟的检索结果；否则使用 SemanticRetriever 接入真实的 RAG 管道。
RAG 不可用时自动降级到 MOCK 知识库。
"""

import json

from langchain_core.tools import tool

from app.config.settings import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


# ══════════════════════════════════════════════════════════════
# 知识检索器
# ══════════════════════════════════════════════════════════════

class KnowledgeRetriever:
    """
    知识检索器

    在 LLM_STUB_MODE=true 时使用占位实现，返回模拟检索结果。
    在 LLM_STUB_MODE=false 时使用 SemanticRetriever 接入真实 RAG 管道
    （embedding → pgvector → 语义检索）。
    RAG 不可用时自动降级到 MOCK 知识库。
    """

    # 模拟知识库：火灾烟雾检测相关 FAQ
    _MOCK_KNOWLEDGE_BASE = [
        {
            "question": "火焰检测的原理是什么",
            "answer": "火焰检测基于深度学习目标检测算法（YOLOv11），通过分析图像中的火焰颜色（红、橙、黄）、形状（不规则、动态变化）和纹理特征，自动识别并定位火焰区域。",
        },
        {
            "question": "烟雾检测的原理是什么",
            "answer": "烟雾检测基于深度学习目标检测算法（YOLOv11），通过分析图像中的烟雾颜色（灰、白、黑）、扩散形态和纹理特征，自动识别并定位烟雾区域。烟雾是火灾的早期征兆，检测烟雾有助于提前预警。",
        },
        {
            "question": "火情等级如何判定",
            "answer": "火情等级根据检测到的火焰和烟雾数量、面积占比综合判定，分为四级：safe（安全，无检测）、notice（注意，少量烟雾）、warning（警告，检测到火焰或较多烟雾）、danger（危险，大面积火焰）。具体阈值由 fire_level_service 根据配置参数动态计算。",
        },
        {
            "question": "如何提高检测准确率",
            "answer": "提高检测准确率的方法包括：1) 使用高质量的训练数据集，确保数据标注准确；2) 调整置信度阈值（conf）和 NMS 阈值（iou）以平衡精度和召回率；3) 使用更强大的模型（如 yolov11l/x）；4) 针对特定场景进行微调训练；5) 使用视频连续帧确认机制减少误报。",
        },
        {
            "question": "YOLOv11 模型的特点",
            "answer": "YOLOv11 是 Ultralytics 最新的目标检测模型，相比 YOLOv8 在精度和速度上都有提升。支持多种规模（n/s/m/l/x），适用于不同算力场景。在火灾烟雾检测中，推荐使用 yolov11n 或 yolov11s 进行实时检测，yolov11l 或 yolov11x 用于高精度离线分析。",
        },
        {
            "question": "火灾烟雾检测的典型应用场景",
            "answer": "典型应用场景包括：1) 森林防火监控（forest）；2) 仓库/厂房火灾监控（warehouse/factory）；3) 建筑物内部火灾监控（building）；4) 施工现场火灾监控（site）；5) 电力设施火灾监控。不同场景可能需要针对性的模型微调。",
        },
    ]

    def __init__(self):
        """初始化知识检索器，延迟创建 SemanticRetriever 实例"""
        self._semantic_retriever = None

    def _get_semantic_retriever(self):
        """延迟获取 SemanticRetriever 单例（避免启动时过早初始化数据库连接）"""
        if self._semantic_retriever is None:
            from app.rag.retriever import SemanticRetriever

            self._semantic_retriever = SemanticRetriever()
            logger.info("SemanticRetriever 已初始化（RAG 模式）")
        return self._semantic_retriever

    def _mock_search(self, query: str, top_k: int = 3) -> list[dict]:
        """
        MOCK 检索：使用关键词匹配模拟检索。

        Args:
            query: 查询文本
            top_k: 返回的最大条目数

        Returns:
            list[dict]: 检索结果列表，每项包含 question 和 answer 字段
        """
        logger.info("知识检索（MOCK 模式）: query=%s, top_k=%d", query, top_k)

        query_lower = query.lower()
        scored = []
        for item in self._MOCK_KNOWLEDGE_BASE:
            score = 0
            item_text = (item["question"] + " " + item["answer"]).lower()
            # 1. 整体查询作为子串匹配（适用于中文连续查询）
            if query_lower in item_text:
                score += 5
            # 2. 按空格分词匹配（适用于英文或有空格分隔的中文关键词）
            for word in query_lower.split():
                if word in item_text:
                    score += 1
            # 3. 逐字符重叠度匹配（适用于中文查询，如"火焰检测原理"匹配"火焰检测的原理"）
            query_chars = set(query_lower.replace(" ", ""))
            item_chars = set(item_text.replace(" ", ""))
            char_overlap = len(query_chars & item_chars) / max(len(query_chars), 1)
            score += int(char_overlap * 3)
            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    def _rag_search(self, query: str, top_k: int = 3) -> list[dict]:
        """
        通过 SemanticRetriever 进行真实 RAG 语义检索。

        Args:
            query: 查询文本
            top_k: 返回的最大条目数

        Returns:
            list[dict]: 检索结果列表，每项包含 question 和 answer 字段
        """
        retriever = self._get_semantic_retriever()
        result = retriever.search(query, top_k=top_k)

        if result.get("status") != "success":
            logger.warning(
                "RAG 检索失败: %s，降级到 MOCK 知识库", result.get("message")
            )
            raise RuntimeError(result.get("message", "RAG 检索返回异常状态"))

        rag_results = result.get("results", [])
        if not rag_results:
            logger.info("RAG 检索无结果: query=%s", query)
            return []

        # 转换 SemanticRetriever 结果格式为 knowledge_tool 统一格式
        converted = []
        for item in rag_results:
            content = item.get("content", "")
            metadata = item.get("metadata", {})
            question = metadata.get("title", query)
            converted.append({"question": question, "answer": content})

        logger.info(
            "RAG 检索成功: query=%s, 返回 %d 条结果", query, len(converted)
        )
        return converted

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """
        检索与查询相关的知识条目。

        在 LLM_STUB_MODE=true 时使用 MOCK 关键词匹配；
        在 LLM_STUB_MODE=false 时使用 SemanticRetriever 进行语义检索。
        RAG 不可用时自动降级到 MOCK 知识库。

        Args:
            query: 查询文本（用户问题或关键词）。
            top_k: 返回的最大条目数，默认 3。

        Returns:
            list[dict]: 检索结果列表，每项包含 question 和 answer 字段。
        """
        # LLM_STUB_MODE 下直接使用 MOCK
        if settings.LLM_STUB_MODE:
            return self._mock_search(query, top_k)

        # 非 stub 模式：尝试 RAG，失败则降级到 MOCK
        try:
            return self._rag_search(query, top_k)
        except Exception as e:
            logger.warning("RAG 检索异常，降级到 MOCK 知识库: %s", e)
            return self._mock_search(query, top_k)


# 全局单例
knowledge_retriever = KnowledgeRetriever()


# ══════════════════════════════════════════════════════════════
# LangChain Tool 封装
# ══════════════════════════════════════════════════════════════

@tool
def search_knowledge(query: str) -> str:
    """检索火灾烟雾检测相关的专业知识。

    适用场景：用户询问火灾检测原理、模型特性、最佳实践等专业知识。

    Args:
        query: 查询问题或关键词，如 "火焰检测原理"、"如何提高检测准确率" 等。

    Returns:
        str: 检索到的知识内容，格式化的问答对。
    """
    try:
        results = knowledge_retriever.search(query, top_k=3)

        if not results:
            return json.dumps({
                "tool": "search_knowledge",
                "status": "error",
                "summary": f"未找到与「{query}」相关的知识内容。当前知识库中暂无相关信息，建议联系管理员更新知识库。"
            }, ensure_ascii=False)

        return json.dumps({
            "tool": "search_knowledge",
            "status": "success",
            "query": query,
            "results": results,
            "summary": f"找到 {len(results)} 条相关知识"
        }, ensure_ascii=False)
    except Exception as e:
        logger.exception("知识检索工具调用失败: query=%s", query)
        return json.dumps({
            "tool": "search_knowledge",
            "status": "error",
            "summary": f"知识检索失败：{str(e)}"
        }, ensure_ascii=False)