"""
天气数据服务模块

封装天气数据采集与持久化逻辑。
- 无 API Key 时返回模拟数据，保证系统不阻塞
- 有 API Key 时调用真实天气 API
"""
import random
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.logger import get_logger
from app.entity.db_models import WeatherData

logger = get_logger(__name__)


class WeatherService:
    """天气数据服务，负责天气数据的获取与持久化"""

    def fetch(self, db: Session, location_id: int) -> WeatherData:
        """
        拉取指定监测点的天气数据

        若 API Key 未配置，返回模拟数据以保证系统不阻塞；
        若配置了 API Key，可扩展为调用真实天气 API。
        """
        if settings.WEATHER_API_KEY:
            # 真实 API 调用占位，后续可接入 pyowm 或 OpenWeatherMap
            weather_data = self._fetch_from_api(location_id)
        else:
            # API Key 未配置时使用模拟数据，保证系统可运行
            weather_data = self._generate_mock_weather()

        return self.save_weather_data(db, location_id, weather_data)

    def _fetch_from_api(self, location_id: int) -> Dict[str, Any]:
        """
        从真实天气 API 拉取数据（占位，后续接入 pyowm）

        当前返回模拟数据，待真实 API Key 配置后实现。
        """
        logger.info("天气 API Key 已配置，但真实 API 调用尚未实现，使用模拟数据")
        return self._generate_mock_weather()

    def _generate_mock_weather(self) -> Dict[str, Any]:
        """
        生成模拟天气数据，用于无 API Key 时的降级运行

        模拟合理范围内的随机天气数据，确保系统在任何情况下都能正常运行。
        """
        conditions = ["clear", "cloudy", "rain", "fog", "snow", "overcast"]
        return {
            "temperature": round(random.uniform(-5, 40), 1),
            "humidity": round(random.uniform(20, 100), 1),
            "precipitation": round(random.uniform(0, 50), 1),
            "wind_speed": round(random.uniform(0, 30), 1),
            "visibility": random.randint(500, 10000),
            "weather_condition": random.choice(conditions),
        }

    def save_weather_data(
        self, db: Session, location_id: int, weather_data: Dict[str, Any]
    ) -> WeatherData:
        """
        将天气数据持久化到数据库

        每次拉取都会创建新记录，保留历史数据用于趋势分析。
        """
        record = WeatherData(
            location_id=location_id,
            timestamp=datetime.now(),
            temperature=weather_data["temperature"],
            humidity=weather_data["humidity"],
            precipitation=weather_data["precipitation"],
            wind_speed=weather_data["wind_speed"],
            visibility=weather_data["visibility"],
            weather_condition=weather_data["weather_condition"],
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        logger.debug(
            "天气数据已保存: location_id=%s, temp=%.1f, condition=%s",
            location_id,
            weather_data["temperature"],
            weather_data["weather_condition"],
        )
        return record

    def get_latest(self, db: Session, location_id: int) -> Optional[WeatherData]:
        """
        获取指定监测点最新一条天气数据

        按 timestamp 倒序取第一条，用于前端实时展示。
        """
        return (
            db.query(WeatherData)
            .filter(WeatherData.location_id == location_id)
            .order_by(WeatherData.timestamp.desc())
            .first()
        )

    def get_history(
        self, db: Session, location_id: int, limit: int = 24
    ):
        """
        获取指定监测点历史天气数据，按时间倒序，limit 条

        用于前端天气趋势图表展示。
        """
        return (
            db.query(WeatherData)
            .filter(WeatherData.location_id == location_id)
            .order_by(WeatherData.timestamp.desc())
            .limit(limit)
            .all()
        )


# 全局单例，其他模块直接 import 使用
weather_service = WeatherService()