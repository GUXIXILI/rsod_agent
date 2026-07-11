"""
定时任务定义

所有周期性任务的注册入口。
"""
from app.core.logger import get_logger

logger = get_logger(__name__)


def register_jobs(scheduler):
    """注册所有定时任务"""
    # 火灾方向当前无定时任务
    # 后续可扩展：定时清理过期检测记录等
    logger.info("定时任务注册完成（当前无定时任务）")