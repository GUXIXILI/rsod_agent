"""
多 Agent 节点函数 — 供 LangGraph 调用

每个节点对应一个专业 Agent，处理特定类型的任务：
  - detection_node: 火灾烟雾检测
  - analysis_node: 数据分析
  - qa_node: 知识问答
"""

import json
from typing import Any, Dict

from app.agent.tools.stats_tool import query_detection_history, query_detection_stats
from app.agent.tools.detection_tool import (
    detect_batch_images,
    detect_single_image,
    detect_video_file,
    detect_zip_images_file,
)
from app.agent.tools.knowledge_tool import search_knowledge
from app.core.logger import get_logger

logger = get_logger(__name__)


def detection_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """检测 Agent 节点：处理图像/视频火灾烟雾检测任务"""
    messages = state["messages"]
    last_message = messages[-1].content
    user_id = state.get("user_id", 1)

    logger.info("Detection Agent 收到请求: %s", last_message[:50])

    try:
        result = {}

        if "[附件视频路径:" in last_message:
            video_path = last_message.split("[附件视频路径:")[1].split("]")[0].strip()
            result_str = detect_video_file.invoke(
                {"video_path": video_path, "user_id": user_id}
            )
            result = json.loads(result_str)
            result["type"] = "video"
        elif "[附件多张图片路径:" in last_message:
            paths = last_message.split("[附件多张图片路径:")[1].split("]")[0].strip()
            image_paths = [p.strip() for p in paths.split(",")]
            result_str = detect_batch_images.invoke(
                {"image_paths": image_paths, "user_id": user_id}
            )
            result = json.loads(result_str)
        elif "[附件图片路径:" in last_message:
            image_path = last_message.split("[附件图片路径:")[1].split("]")[0].strip()
            if image_path.endswith(".zip"):
                result_str = detect_zip_images_file.invoke(
                    {"zip_path": image_path, "user_id": user_id}
                )
                result = json.loads(result_str)
            else:
                result_str = detect_single_image.invoke(
                    {"image_path": image_path, "user_id": user_id}
                )
                result = json.loads(result_str)

        return {"detection_result": result}
    except Exception as e:
        logger.error("Detection Agent 执行失败: %s", str(e))
        return {"detection_result": {"error": str(e)}}


def analysis_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """分析 Agent 节点：处理检测统计和历史查询任务"""
    messages = state["messages"]
    last_message = messages[-1].content

    logger.info("Analysis Agent 收到请求: %s", last_message[:50])

    try:
        result = {}

        if "今天" in last_message or "最近" in last_message or "统计" in last_message:
            result_str = query_detection_stats.invoke({})
        elif "历史" in last_message or "记录" in last_message:
            result_str = query_detection_history.invoke({"page": 1, "page_size": 10})
        else:
            result_str = query_detection_stats.invoke({})

        # stats_tool 返回的是格式化的纯文本字符串，不是 JSON
        # 将其包装为 analysis_result 供 Supervisor 汇总使用
        result = {"stats_text": result_str}

        return {"analysis_result": result}
    except Exception as e:
        logger.error("Analysis Agent 执行失败: %s", str(e))
        return {"analysis_result": {"error": str(e)}}


def qa_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """问答 Agent 节点：处理知识问答任务"""
    messages = state["messages"]
    last_message = messages[-1].content

    logger.info("QA Agent 收到请求: %s", last_message[:50])

    try:
        results_str = search_knowledge.invoke({"query": last_message})
        results = json.loads(results_str)
        return {"qa_result": results}
    except Exception as e:
        logger.error("QA Agent 执行失败: %s", str(e))
        return {"qa_result": {"error": str(e)}}