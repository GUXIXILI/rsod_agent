"""
危险路况预测服务模块

封装多模态融合预测逻辑：
- 结合天气数据、交通数据、检测结果，输出风险等级
- 模型不可用时使用规则降级，保证系统可用性
- 预测结果持久化到 RoadHazardPrediction 表
"""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.logger import get_logger
from app.entity.db_models import RoadHazardPrediction, WeatherData, TrafficData

logger = get_logger(__name__)


class HazardPredictService:
    """危险路况预测服务，融合多源数据输出风险等级"""

    # 风险等级定义
    RISK_LEVELS = ["low", "medium", "high", "critical"]

    def predict(
        self, db: Session, location_id: int, horizon_minutes: int = 30
    ) -> RoadHazardPrediction:
        """
        执行危险路况预测

        1. 获取最近时间窗口内的天气和交通数据
        2. 若预测模型可用，加载模型预测；否则使用规则降级
        3. 将预测结果写入 RoadHazardPrediction 表
        """
        # 获取最近天气数据
        latest_weather = (
            db.query(WeatherData)
            .filter(WeatherData.location_id == location_id)
            .order_by(WeatherData.timestamp.desc())
            .first()
        )

        # 获取最近交通数据
        latest_traffic = (
            db.query(TrafficData)
            .filter(TrafficData.location_id == location_id)
            .order_by(TrafficData.timestamp.desc())
            .first()
        )

        # 收集特征向量
        features = self._build_features(latest_weather, latest_traffic)

        # 尝试加载模型预测，失败则降级为规则预测
        model_path = self._get_model_path(location_id)
        if model_path:
            risk_level, risk_probability = self._predict_with_model(
                features, model_path
            )
        else:
            # 模型不可用时使用规则降级，保证系统可用性
            risk_level, risk_probability = self._predict_with_rules(features)

        # 持久化预测结果
        prediction = RoadHazardPrediction(
            location_id=location_id,
            prediction_time=datetime.now(),
            horizon_minutes=horizon_minutes,
            risk_level=risk_level,
            risk_probability=risk_probability,
            model_type="rules" if not model_path else "xgboost",
            feature_summary={
                "temperature": features.get("temperature"),
                "humidity": features.get("humidity"),
                "precipitation": features.get("precipitation"),
                "wind_speed": features.get("wind_speed"),
                "visibility": features.get("visibility"),
                "vehicle_count": features.get("vehicle_count"),
                "avg_speed": features.get("avg_speed"),
                "density": features.get("density"),
            },
        )
        db.add(prediction)
        db.commit()
        db.refresh(prediction)

        logger.info(
            "路况预测完成: location_id=%s, risk_level=%s, probability=%.2f",
            location_id,
            risk_level,
            risk_probability,
        )
        return prediction

    def _build_features(
        self,
        weather: Optional[WeatherData],
        traffic: Optional[TrafficData],
    ) -> Dict[str, Any]:
        """构建特征向量，处理数据缺失情况"""
        features = {
            "temperature": 25.0,
            "humidity": 60.0,
            "precipitation": 0.0,
            "wind_speed": 10.0,
            "visibility": 10000,
            "weather_condition": "clear",
            "vehicle_count": 0,
            "avg_speed": 60.0,
            "density": 0.0,
        }
        if weather:
            features.update({
                "temperature": weather.temperature or 25.0,
                "humidity": weather.humidity or 60.0,
                "precipitation": weather.precipitation or 0.0,
                "wind_speed": weather.wind_speed or 10.0,
                "visibility": weather.visibility or 10000,
                "weather_condition": weather.weather_condition or "clear",
            })
        if traffic:
            features.update({
                "vehicle_count": traffic.vehicle_count or 0,
                "avg_speed": traffic.avg_speed or 60.0,
                "density": traffic.density or 0.0,
            })
        return features

    def _predict_with_rules(
        self, features: Dict[str, Any]
    ):
        """
        规则降级预测：根据天气和交通条件综合判断风险等级

        规则设计思路：
        - 极端天气(暴雨/暴雪/大雾) + 高密度交通 → critical
        - 恶劣天气(雨/雪/雾) + 中高密度交通 → high
        - 一般天气但有较高交通密度 → medium
        - 正常天气 + 低密度交通 → low
        """
        risk_score = 0.0

        # 天气因素评分（0-50 分）
        condition = features.get("weather_condition", "clear")
        if condition in ("snow", "fog"):
            risk_score += 35
        elif condition == "rain":
            risk_score += 25
        elif condition in ("overcast", "cloudy"):
            risk_score += 10

        # 降水量评分（0-20 分）
        precipitation = features.get("precipitation", 0)
        if precipitation > 30:
            risk_score += 20
        elif precipitation > 10:
            risk_score += 10

        # 能见度评分（0-20 分）
        visibility = features.get("visibility", 10000)
        if visibility < 500:
            risk_score += 20
        elif visibility < 2000:
            risk_score += 10

        # 风速评分（0-10 分）
        wind_speed = features.get("wind_speed", 10)
        if wind_speed > 20:
            risk_score += 10

        # 交通密度评分（0-30 分）
        density = features.get("density", 0)
        if density > 0.8:
            risk_score += 30
        elif density > 0.5:
            risk_score += 20
        elif density > 0.3:
            risk_score += 10

        # 平均车速评分（0-20 分）
        avg_speed = features.get("avg_speed", 60)
        if avg_speed < 20:
            risk_score += 15  # 严重拥堵
        elif avg_speed > 100:
            risk_score += 20  # 车速过快

        # 风险等级映射
        if risk_score >= 70:
            risk_level = "critical"
        elif risk_score >= 50:
            risk_level = "high"
        elif risk_score >= 30:
            risk_level = "medium"
        else:
            risk_level = "low"

        risk_probability = min(risk_score / 100.0, 0.99)

        logger.debug(
            "规则预测: risk_score=%.1f, risk_level=%s, probability=%.2f",
            risk_score,
            risk_level,
            risk_probability,
        )
        return risk_level, risk_probability

    def _get_model_path(self, location_id: int) -> Optional[str]:
        """
        获取预测模型文件路径（占位，后续加载已训练的 XGBoost/LSTM 模型）

        当前始终返回 None，触发规则降级。
        后续可根据 location_id 查找对应的模型文件路径。
        """
        return None

    def _predict_with_model(
        self, features: Dict[str, Any], model_path: str
    ):
        """
        使用已训练模型预测（占位，后续加载 XGBoost/LSTM）

        当前直接返回规则降级结果，待模型训练完成后实现。
        """
        logger.info("模型预测路径已配置但尚未实现，降级为规则预测")
        return self._predict_with_rules(features)

    def get_predictions(
        self, db: Session, location_id: int, limit: int = 20
    ):
        """获取指定监测点的预测历史"""
        return (
            db.query(RoadHazardPrediction)
            .filter(RoadHazardPrediction.location_id == location_id)
            .order_by(RoadHazardPrediction.prediction_time.desc())
            .limit(limit)
            .all()
        )


# 全局单例
hazard_predict_service = HazardPredictService()