"""
定时任务调度模块

使用 apscheduler 管理周期性任务：
- 天气数据定时拉取（每 15 分钟）
- 后续可扩展交通数据拉取、预测模型定期评估等

若 apscheduler 未安装或 SCHEDULER_ENABLED=false，调度器不会启动，
但不会阻塞主服务运行。
"""
from app.config.settings import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# 全局调度器实例（延迟初始化，避免 apscheduler 未安装时导入失败）
scheduler = None


def start_scheduler():
    """启动调度器，注册所有定时任务"""
    if not settings.SCHEDULER_ENABLED:
        logger.info("定时任务调度器已禁用（SCHEDULER_ENABLED=false）")
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        # apscheduler 未安装，记录警告但不阻塞服务启动
        logger.warning("apscheduler 未安装，定时任务调度器不可用。请运行 pip install apscheduler")
        return

    global scheduler
    scheduler = BackgroundScheduler()

    # 导入调度任务（延迟导入避免循环依赖）
    from app.scheduler.jobs import register_jobs

    register_jobs(scheduler)
    scheduler.start()
    logger.info("定时任务调度器已启动")


def stop_scheduler():
    """停止调度器，等待当前任务执行完毕"""
    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("定时任务调度器已停止")
