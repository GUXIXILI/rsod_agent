"""
定时任务定义

所有周期性任务的注册入口。
"""
from app.core.logger import get_logger

logger = get_logger(__name__)


def register_jobs(scheduler):
    """注册所有定时任务"""
    # 每 15 分钟拉取一次天气数据
    scheduler.add_job(
        fetch_weather_job,
        trigger="interval",
        minutes=15,
        id="fetch_weather",
        name="天气数据定时拉取",
        replace_existing=True,
    )
    logger.info("已注册定时任务: fetch_weather（每 15 分钟）")


def fetch_weather_job():
    """
    定时拉取天气数据（占位，后续实现）

    遍历所有活跃监测点，调用 weather_service.fetch() 拉取天气数据。
    当前仅记录日志，待数据库连接和 weather_service 可用后实现。
    """
    logger.info("天气数据定时拉取任务触发（占位，待实现）")
    # 后续实现：
    # from app.database.session import SessionLocal
    # from app.services.weather_service import weather_service
    # from app.entity.db_models import DetectionScene
    # db = SessionLocal()
    # try:
    #     scenes = db.query(DetectionScene).filter(DetectionScene.is_active == True).all()
    #     for scene in scenes:
    #         weather_service.fetch(db, scene.id)
    # finally:
    #     db.close()
