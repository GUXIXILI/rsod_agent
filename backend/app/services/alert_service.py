"""
火灾预警服务模块

根据检测结果生成并分发火灾预警：
- 火情等级为 notice/warning/danger 时自动创建预警记录
- 推送渠道占位（站内信/邮件/WebSocket），后续可扩展
"""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.logger import get_logger

logger = get_logger(__name__)


class AlertService:
    """火灾预警服务，负责预警的生成与分发"""

    def create_alert(
        self, db: Session, task, fire_level_result: dict
    ):
        """
        根据检测结果创建火灾预警

        仅当火情等级为 notice/warning/danger 时生成预警。
        safe 级别不触发预警。
        """
        from app.entity.db_models import FireAlert

        fire_level = fire_level_result.get("fire_level", "safe")
        if fire_level not in ("notice", "warning", "danger"):
            logger.debug(
                "火情等级为 %s，未达到预警阈值，跳过预警生成",
                fire_level,
            )
            return None

        # 生成预警内容
        content = self._build_alert_content(task, fire_level_result)
        suggestion = self._build_suggestion(fire_level)

        # 创建预警记录
        alert = FireAlert(
            task_id=task.id,
            scene_id=task.scene_id,
            fire_level=fire_level,
            content=content,
            suggestion=suggestion,
            channels=["internal"],
            push_status="pending",
            handled_status="unhandled",
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        logger.info(
            "火灾预警已生成: alert_id=%s, level=%s, scene_id=%s",
            alert.id,
            alert.fire_level,
            alert.scene_id,
        )

        # 推送预警（占位）
        self._dispatch_alert(alert)
        db.commit()
        db.refresh(alert)

        return alert

    def _build_alert_content(self, task, fire_level_result: dict) -> str:
        """构建火灾预警内容文本"""
        contents = {
            "notice": "检测到疑似烟雾/火苗，请保持关注",
            "warning": "检测到明显火情（warning）",
            "danger": "检测到严重火情（danger）",
        }
        return contents.get(
            fire_level_result.get("fire_level"),
            f"监控点 {task.scene_id} 检测到异常火情",
        )

    def _build_suggestion(self, fire_level: str) -> str:
        """根据火情等级生成处置建议"""
        suggestions = {
            "notice": "安排人员现场复核，确认是否为初期火情。",
            "warning": "立即启动现场核查，准备启动消防预案。",
            "danger": "立即疏散人员并拨打119，启动消防设备。",
        }
        return suggestions.get(fire_level, "")

    def _dispatch_alert(self, alert):
        """分发预警并更新推送状态"""
        logger.info(
            "火灾预警分发: alert_id=%s, channels=%s",
            alert.id,
            alert.channels,
        )
        alert.push_status = "dispatched"
        alert.pushed_at = datetime.now(timezone.utc)

    def get_alerts(
        self,
        db: Session,
        user_id: int,
        scene_id: Optional[int] = None,
        limit: int = 50,
    ) -> List["FireAlert"]:
        """获取火灾预警列表，按用户关联的检测任务过滤，可按监控点筛选"""
        from app.entity.db_models import DetectionTask, FireAlert

        query = (
            db.query(FireAlert)
            .join(DetectionTask, FireAlert.task_id == DetectionTask.id)
            .filter(DetectionTask.user_id == user_id)
            .order_by(FireAlert.created_at.desc())
        )
        if scene_id is not None:
            query = query.filter(FireAlert.scene_id == scene_id)
        return query.limit(limit).all()

    def handle_alert(self, db: Session, alert_id: int):
        """标记预警为已处理"""
        from app.entity.db_models import FireAlert

        alert = db.query(FireAlert).filter(FireAlert.id == alert_id).first()
        if alert is None:
            raise ValueError(f"预警不存在: alert_id={alert_id}")

        alert.handled_status = "resolved"
        alert.handled_at = datetime.now()
        alert.push_status = "sent"
        db.commit()
        db.refresh(alert)

        logger.info("火灾预警已处理: alert_id=%s", alert_id)
        return alert


# 全局单例
alert_service = AlertService()