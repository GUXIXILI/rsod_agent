"""
Agent 工具模块 — 统一导出所有工具函数

支持两种导入方式：
  1. from app.agent.tools import detect_single_image  （扁平导入，兼容 test_agent.py）
  2. from app.agent.tools.detection_tool import detect_single_image  （模块化导入）
"""

from app.agent.tools.detection_tool import (
    detect_single_image,
    detect_batch_images,
    detect_zip_images_file,
    detect_video_file,
)
from app.agent.tools.knowledge_tool import search_knowledge
from app.agent.tools.stats_tool import query_detection_stats, query_detection_history
from app.agent.tools.user_tool import query_user_list

__all__ = [
    "detect_single_image",
    "detect_batch_images",
    "detect_zip_images_file",
    "detect_video_file",
    "search_knowledge",
    "query_detection_stats",
    "query_detection_history",
    "query_user_list",
]