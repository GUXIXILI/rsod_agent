"""
定时任务定义

所有周期性任务的注册入口。
"""
import logging
from datetime import datetime, timedelta

from app.core.logger import get_logger

logger = get_logger(__name__)


def cleanup_expired_tasks():
    """清理30天前状态为failed的检测任务记录"""
    from app.database.session import SessionLocal
    from app.entity.db_models import DetectionTask
    db = None
    try:
        db = SessionLocal()
        threshold = datetime.now() - timedelta(days=30)
        deleted = db.query(DetectionTask).filter(
            DetectionTask.status == "failed",
            DetectionTask.created_at < threshold
        ).delete(synchronize_session=False)
        db.commit()
        if deleted > 0:
            logger.info("清理了 %d 条过期检测任务", deleted)
    except Exception as e:
        logger.error("清理过期任务失败: %s", e)
        if db is not None:
            db.rollback()
    finally:
        if db is not None:
            db.close()


def register_jobs(scheduler):
    """注册所有定时任务"""
    scheduler.add_job(cleanup_expired_tasks, 'cron', hour=3, minute=0, id='cleanup_expired')
    logger.info("定时任务注册完成: cleanup_expired_tasks (每天 03:00)")
