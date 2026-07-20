"""
统计查询工具封装模块

封装检测统计和历史查询工具，供 ReAct Agent 在推理过程中调用。

提供两个工具：
- query_detection_stats：查询检测统计概览（总检测次数、火情分布、趋势）
- query_detection_history：查询检测历史记录（分页、筛选）
"""

import json
from typing import Optional

from langchain_core.tools import tool

from app.database.session import SessionLocal
from app.services.stats_service import stats_service
from app.services.history_service import history_service
from app.core.logger import get_logger

logger = get_logger(__name__)


@tool
def query_detection_stats() -> str:
    """查询当前用户的检测统计概览数据。

    统计内容包括：
    - 总检测次数
    - 检出火焰的次数
    - 检出烟雾的次数
    - 触发预警的次数
    - 火情等级分布
    - 最近 7 天检测趋势

    Returns:
        str: 格式化的检测统计数据摘要。
    """
    db = SessionLocal()
    try:
        # 使用默认用户 ID=1（Agent 调用时的系统用户）
        overview = stats_service.get_overview(db, user_id=1)
        fire_distribution = stats_service.get_fire_level_distribution(db, user_id=1)
        trend = stats_service.get_trend(db, user_id=1, days=7)

        level_names = {
            "safe": "安全",
            "notice": "注意",
            "warning": "警告",
            "danger": "危险",
        }

        result = {
            "tool": "query_detection_stats",
            "status": "success",
            "summary": f"总检测 {overview['total_detections']} 次，检出火焰 {overview['fire_detected']} 次，检出烟雾 {overview['smoke_detected']} 次，触发预警 {overview['warning_count']} 次",
            "data": {
                "overview": {
                    "total_detections": overview["total_detections"],
                    "fire_detected": overview["fire_detected"],
                    "smoke_detected": overview["smoke_detected"],
                    "warning_count": overview["warning_count"],
                },
                "fire_distribution": [
                    {
                        "fire_level": item["fire_level"],
                        "fire_level_cn": level_names.get(item["fire_level"], item["fire_level"]),
                        "count": item["count"],
                    }
                    for item in fire_distribution
                ],
                "trend": [
                    {
                        "date": item["date"],
                        "count": item["count"],
                    }
                    for item in trend
                ],
            }
        }
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        logger.exception("统计查询工具调用失败")
        return json.dumps({"tool": "query_detection_stats", "status": "error", "summary": f"统计查询失败：{str(e)}", "data": None}, ensure_ascii=False, default=str)
    finally:
        db.close()


@tool
def query_detection_history(
    page: int = 1,
    page_size: int = 10,
    fire_level: Optional[str] = None,
    file_name: Optional[str] = None,
) -> str:
    """查询检测历史记录，支持分页和筛选。

    适用场景：用户需要查看历史检测记录，了解检测情况。

    Args:
        page: 页码，从 1 开始，默认 1。
        page_size: 每页条数，默认 10。
        fire_level: 按火情等级筛选，可选值：safe/notice/warning/danger，为空则不筛选。
        file_name: 按文件名模糊搜索，为空则不筛选。

    Returns:
        str: 格式化的检测历史记录列表。
    """
    db = SessionLocal()
    try:
        result = history_service.get_tasks(
            db=db,
            user_id=1,
            page=page,
            page_size=page_size,
            fire_level=fire_level,
            file_name=file_name,
        )

        total = result["total"]
        items = result["items"]

        level_names = {
            "safe": "安全",
            "notice": "注意",
            "warning": "警告",
            "danger": "危险",
        }

        total_pages = max(1, (total + page_size - 1) // page_size)

        result = {
            "tool": "query_detection_history",
            "status": "success",
            "summary": f"第 {page} 页，共 {total_pages} 页，总记录数 {total}",
            "data": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "items": [
                    {
                        "task_type": item.get("task_type"),
                        "file_name": item.get("file_name"),
                        "fire_level": item.get("fire_level"),
                        "fire_level_cn": level_names.get(item.get("fire_level", ""), item.get("fire_level", "未知")),
                        "fire_object_count": item.get("fire_object_count", 0),
                        "smoke_object_count": item.get("smoke_object_count", 0),
                        "created_at": str(item.get("created_at", ""))[:19] if item.get("created_at") else None,
                    }
                    for item in items
                ],
            }
        }
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        logger.exception("历史查询工具调用失败")
        return json.dumps({"tool": "query_detection_history", "status": "error", "summary": f"历史查询失败：{str(e)}", "data": None}, ensure_ascii=False, default=str)
    finally:
        db.close()