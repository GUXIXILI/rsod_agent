"""
预警服务模块

根据预测结果生成并分发预警：
- 高风险（high/critical）时自动创建预警记录
- 推送渠道占位（站内信/邮件/WebSocket），后续可扩展
"""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.entity.db_models import HazardAlert, RoadHazardPrediction

logger = get_logger(__name__)


class AlertService:
    """预警服务，负责预警的生成与分发"""

    def create_alert(
        self, db: Session, prediction: RoadHazardPrediction
    ) -> Optional[HazardAlert]:
        """
        根据预测结果创建预警

        仅当预测风险等级为 high 或 critical 时生成预警。
        低风险和中风险不触发预警，仅记录预测结果。
        """
        if prediction.risk_level not in ("high", "critical"):
            logger.debug(
                "风险等级为 %s，未达到预警阈值，跳过预警生成",
                prediction.risk_level,
            )
            return None

        # 生成预警内容
        content = self._build_alert_content(prediction)

        # 创建预警记录
        alert = HazardAlert(
            location_id=prediction.location_id,
            alert_level=prediction.risk_level,
            content=content,
            channels=["internal"],  # 推送渠道：internal（站内信），后续可扩展 email/sms/websocket
            push_status="pending",
            handled_status="pending",
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        logger.info(
            "预警已生成: alert_id=%s, level=%s, location_id=%s",
            alert.id,
            alert.alert_level,
            alert.location_id,
        )

        # 推送预警（占位，后续根据 channels 配置分发到不同渠道）
        self._dispatch_alert(alert)

        return alert

    def _build_alert_content(self, prediction: RoadHazardPrediction) -> str:
        """
        构建预警内容文本

        根据风险等级和特征摘要生成人类可读的预警信息。
        """
        level_map = {
            "high": "高风险",
            "critical": "极高风险",
        }
        risk_text = level_map.get(prediction.risk_level, "异常")

        feature = prediction.feature_summary or {}
        weather_cond = feature.get("weather_condition", "未知")
        visibility = feature.get("visibility", "未知")
        density = feature.get("density", 0)

        return (
            f"[{risk_text}] 监测点 {prediction.location_id} "
            f"预测未来路况风险等级为 {risk_text}，"
            f"风险概率 {prediction.risk_probability:.1%}。"
            f"天气：{weather_cond}，能见度：{visibility}m，"
            f"交通密度：{density:.2f}。"
            f"建议加强监控，必要时采取限速或分流措施。"
        )

    def _dispatch_alert(self, alert: HazardAlert):
        """
        分发预警到各渠道（占位，后续扩展）

        当前仅记录日志，后续可接入：
        - 站内信系统（数据库写入 + WebSocket 推送）
        - 邮件通知（SMTP）
        - 短信通知（SMS API）
        """
        logger.info(
            "预警分发: alert_id=%s, channels=%s",
            alert.id,
            alert.channels,
        )

    def get_alerts(
        self, db: Session, location_id: Optional[int] = None, limit: int = 50
    ):
        """
        获取预警列表

        可按监测点筛选，按创建时间倒序。
        """
        query = db.query(HazardAlert).order_by(HazardAlert.created_at.desc())
        if location_id is not None:
            query = query.filter(HazardAlert.location_id == location_id)
        return query.limit(limit).all()

    def handle_alert(self, db: Session, alert_id: int) -> HazardAlert:
        """
        标记预警为已处理

        更新 handled_status 和 handled_at 时间戳。
        """
        alert = db.query(HazardAlert).filter(HazardAlert.id == alert_id).first()
        if alert is None:
            raise ValueError(f"预警不存在: alert_id={alert_id}")

        alert.handled_status = "handled"
        alert.handled_at = datetime.now()
        alert.push_status = "delivered"
        db.commit()
        db.refresh(alert)

        logger.info("预警已处理: alert_id=%s", alert_id)
        return alert


# 全局单例
alert_service = AlertService()