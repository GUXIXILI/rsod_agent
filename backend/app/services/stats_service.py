"""
数据看板统计服务

提供检测统计数据的查询：
- 总览统计（总检测次数、检出次数、预警次数）
- 火情等级分布
- 检测趋势
"""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.entity.db_models import DetectionTask, FireAlert, DetectionResult, DetectionScene


class StatsService:
    """数据看板统计服务"""

    def _get_growth(self, db: Session, user_id: int, metric: str, days: int = 30) -> float:
        """
        计算指定指标在当前周期（最近 days 天）相对于上一周期（前 days 天）的增长率（%）。
        如果上一周期为 0，返回 100.0（若当前 > 0）或 0.0（若都为 0）。
        """
        now = datetime.now()
        current_start = now - timedelta(days=days)
        prev_start = current_start - timedelta(days=days)

        # 构造查询当前值和上期值
        def count_query(start_date, end_date):
            q = db.query(func.count(DetectionTask.id)).filter(
                DetectionTask.user_id == user_id,
                DetectionTask.created_at >= start_date,
                DetectionTask.created_at < end_date
            )
            if metric == 'fire':
                q = q.filter(DetectionTask.fire_object_count > 0)
            elif metric == 'smoke':
                q = q.filter(DetectionTask.smoke_object_count > 0)
            elif metric == 'warning':
                q = q.filter(DetectionTask.fire_level.in_(["warning", "danger"]))
            # total - без дополнительных фильтров
            return q.scalar() or 0

        current_val = count_query(current_start, now)
        prev_val = count_query(prev_start, current_start)

        if prev_val == 0:
            return 100.0 if current_val > 0 else 0.0
        return ((current_val - prev_val) / prev_val) * 100.0

    def get_overview(self, db: Session, user_id: int) -> dict:
        """获取总览统计数据（含环比增长率）"""
        # 基础绝对值
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

        # 环比增长率（最近30天 vs 前30天）
        growth_total = self._get_growth(db, user_id, 'total')
        growth_fire = self._get_growth(db, user_id, 'fire')
        growth_smoke = self._get_growth(db, user_id, 'smoke')
        growth_warning = self._get_growth(db, user_id, 'warning')

        return {
            "total_detections": total,
            "fire_detected": fire_detected,
            "smoke_detected": smoke_detected,
            "warning_count": warning_count,
            "total_detections_growth": growth_total,
            "fire_detected_growth": growth_fire,
            "smoke_detected_growth": growth_smoke,
            "warning_count_growth": growth_warning,
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