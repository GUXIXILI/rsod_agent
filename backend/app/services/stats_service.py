"""
数据看板统计服务

提供检测统计数据的查询：
- 总览统计（总检测次数、检出次数、预警次数）
- 火情等级分布
- 检测趋势
"""
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.entity.db_models import DetectionTask, DetectionResult, DetectionScene


class StatsService:
    """数据看板统计服务"""

    def get_overview(self, db: Session, user_id: int) -> dict:
        """获取总览统计数据"""
        total = db.query(func.count(DetectionTask.id)).filter(
            DetectionTask.user_id == user_id
        ).scalar() or 0

        fire_detected = db.query(func.count(DetectionTask.id)).filter(
            DetectionTask.user_id == user_id,
            DetectionTask.fire_object_count > 0,
        ).scalar() or 0

        smoke_detected = db.query(func.count(DetectionTask.id)).filter(
            DetectionTask.user_id == user_id,
            DetectionTask.smoke_object_count > 0,
        ).scalar() or 0

        warning_count = db.query(func.count(DetectionTask.id)).filter(
            DetectionTask.user_id == user_id,
            DetectionTask.fire_level.in_(["warning", "danger"]),
        ).scalar() or 0

        return {
            "total_detections": total,
            "fire_detected": fire_detected,
            "smoke_detected": smoke_detected,
            "warning_count": warning_count,
        }

    def get_fire_level_distribution(self, db: Session, user_id: int) -> list:
        """获取火情等级分布"""
        results = (
            db.query(
                DetectionTask.fire_level,
                func.count(DetectionTask.id).label("count"),
            )
            .filter(DetectionTask.user_id == user_id)
            .group_by(DetectionTask.fire_level)
            .all()
        )
        return [
            {"fire_level": r.fire_level or "unknown", "count": r.count}
            for r in results
        ]

    def get_trend(self, db: Session, user_id: int, days: int = 7) -> list:
        """获取最近 N 天检测趋势"""
        start_date = datetime.now() - timedelta(days=days)
        results = (
            db.query(
                func.date(DetectionTask.created_at).label("date"),
                func.count(DetectionTask.id).label("count"),
            )
            .filter(
                DetectionTask.user_id == user_id,
                DetectionTask.created_at >= start_date,
            )
            .group_by(func.date(DetectionTask.created_at))
            .order_by(func.date(DetectionTask.created_at))
            .all()
        )
        return [
            {"date": str(r.date), "count": r.count}
            for r in results
        ]

    def get_class_distribution(self, db: Session, user_id: int, days: int = 30) -> list:
        """获取类别分布统计"""
        start_date = datetime.now() - timedelta(days=days)
        results = (
            db.query(DetectionResult.class_name, func.count(DetectionResult.id).label("count"))
            .join(DetectionTask, DetectionResult.task_id == DetectionTask.id)
            .filter(DetectionTask.user_id == user_id, DetectionTask.created_at >= start_date)
            .group_by(DetectionResult.class_name)
            .order_by(func.count(DetectionResult.id).desc())
            .all()
        )
        return [{"class_name": r.class_name, "count": r.count} for r in results]

    def get_scene_distribution(self, db: Session, user_id: int, days: int = 30) -> list:
        """获取场景分布统计"""
        start_date = datetime.now() - timedelta(days=days)
        results = (
            db.query(DetectionScene.name, func.count(DetectionTask.id).label("count"))
            .join(DetectionTask, DetectionScene.id == DetectionTask.scene_id)
            .filter(DetectionTask.user_id == user_id, DetectionTask.created_at >= start_date)
            .group_by(DetectionScene.name)
            .order_by(func.count(DetectionTask.id).desc())
            .all()
        )
        return [{"scene_name": r.name, "count": r.count} for r in results]

    def get_type_distribution(self, db: Session, user_id: int, days: int = 30) -> list:
        """获取任务类型分布统计"""
        start_date = datetime.now() - timedelta(days=days)
        results = (
            db.query(DetectionTask.task_type, func.count(DetectionTask.id).label("count"))
            .filter(DetectionTask.user_id == user_id, DetectionTask.created_at >= start_date)
            .group_by(DetectionTask.task_type)
            .all()
        )
        return [{"task_type": r.task_type, "count": r.count} for r in results]


# 单例
stats_service = StatsService()