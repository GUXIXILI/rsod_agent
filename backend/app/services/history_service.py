"""
检测历史记录服务

提供检测任务的分页查询、筛选、详情查看和删除功能。
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.entity.db_models import DetectionResult, DetectionTask, DetectionScene


class HistoryService:
    """检测历史记录服务"""

    def get_tasks(
        self,
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        fire_level: Optional[str] = None,
        file_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> dict:
        """分页查询检测历史"""
        query = db.query(DetectionTask).filter(DetectionTask.user_id == user_id)

        if fire_level:
            query = query.filter(DetectionTask.fire_level == fire_level)
        if file_name:
            query = query.filter(DetectionTask.file_name.ilike(f"%{file_name}%"))
        if start_time:
            query = query.filter(DetectionTask.created_at >= start_time)
        if end_time:
            query = query.filter(DetectionTask.created_at <= end_time)

        total = query.count()
        tasks = (
            query.order_by(desc(DetectionTask.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "id": t.id,
                    "scene_id": t.scene_id,
                    "task_type": t.task_type,
                    "file_name": t.file_name,
                    "status": t.status,
                    "fire_level": t.fire_level,
                    "fire_object_count": t.fire_object_count,
                    "smoke_object_count": t.smoke_object_count,
                    "annotated_url": t.annotated_url,
                    "created_at": t.created_at,
                }
                for t in tasks
            ],
        }

    def get_task_detail(self, db: Session, task_id: int, user_id: int) -> Optional[dict]:
        """获取检测任务详情，包含所有检测结果"""
        task = (
            db.query(DetectionTask)
            .filter(DetectionTask.id == task_id, DetectionTask.user_id == user_id)
            .first()
        )
        if not task:
            return None

        results = (
            db.query(DetectionResult)
            .filter(DetectionResult.task_id == task_id)
            .all()
        )

        return {
            "id": task.id,
            "user_id": task.user_id,
            "scene_id": task.scene_id,
            "task_type": task.task_type,
            "file_name": task.file_name,
            "status": task.status,
            "fire_level": task.fire_level,
            "fire_area": task.fire_area,
            "smoke_area": task.smoke_area,
            "fire_object_count": task.fire_object_count,
            "smoke_object_count": task.smoke_object_count,
            "original_url": task.original_url,
            "annotated_url": task.annotated_url,
            "image_width": task.image_width,
            "image_height": task.image_height,
            "created_at": task.created_at,
            "results": [
                {
                    "id": r.id,
                    "class_name": r.class_name,
                    "confidence": r.confidence,
                    "x_min": r.x_min,
                    "y_min": r.y_min,
                    "x_max": r.x_max,
                    "y_max": r.y_max,
                    "width": r.width,
                    "height": r.height,
                    "area": r.area,
                }
                for r in results
            ],
        }

    def delete_task(self, db: Session, task_id: int, user_id: int) -> bool:
        """删除检测记录（仅允许删除自己的记录）"""
        task = (
            db.query(DetectionTask)
            .filter(DetectionTask.id == task_id, DetectionTask.user_id == user_id)
            .first()
        )
        if not task:
            return False
        db.delete(task)
        db.commit()
        return True

    def get_summary(self, db: Session, user_id: int) -> dict:
        """获取历史记录汇总"""
        from sqlalchemy import func
        total = db.query(func.count(DetectionTask.id)).filter(
            DetectionTask.user_id == user_id
        ).scalar() or 0
        completed = db.query(func.count(DetectionTask.id)).filter(
            DetectionTask.user_id == user_id, DetectionTask.status == "completed"
        ).scalar() or 0
        failed = db.query(func.count(DetectionTask.id)).filter(
            DetectionTask.user_id == user_id, DetectionTask.status == "failed"
        ).scalar() or 0
        return {"total": total, "completed": completed, "failed": failed}

    def get_scenes(self, db: Session, user_id: int) -> list:
        """获取用户使用过的检测场景列表"""
        results = (
            db.query(DetectionScene.id, DetectionScene.name)
            .join(DetectionTask, DetectionScene.id == DetectionTask.scene_id)
            .filter(DetectionTask.user_id == user_id)
            .distinct()
            .all()
        )
        return [{"id": r.id, "name": r.name} for r in results]


# 单例
history_service = HistoryService()