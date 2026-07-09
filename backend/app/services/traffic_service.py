"""
交通数据服务模块

封装交通数据导入与查询逻辑。
- 支持从 JSONL 文件批量导入 DETRAC 元数据
- 提供按监测点查询最新/历史交通数据
"""
import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.entity.db_models import TrafficData

logger = get_logger(__name__)


class TrafficService:
    """交通数据服务，负责交通数据的导入与查询"""

    def import_metadata(
        self, db: Session, jsonl_path: str, location_id: int
    ) -> int:
        """
        从 JSONL 文件批量导入 DETRAC 元数据

        解析 extract_metadata.py 输出的 JSONL 文件，
        将每帧的交通数据写入 TrafficData 表。
        返回成功导入的记录数。
        """
        imported_count = 0
        try:
            with open(jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        # 数据校验：车速非负，车流量非负
                        vehicle_count = record.get("vehicle_count", 0)
                        avg_speed = record.get("avg_speed", 0)
                        if vehicle_count < 0 or avg_speed < 0:
                            logger.warning(
                                "跳过无效数据: vehicle_count=%s, avg_speed=%s",
                                vehicle_count,
                                avg_speed,
                            )
                            continue

                        traffic = TrafficData(
                            location_id=location_id,
                            timestamp=datetime.fromisoformat(
                                record.get("timestamp", str(datetime.now()))
                            ),
                            vehicle_count=vehicle_count,
                            avg_speed=avg_speed,
                            vehicle_types=record.get("vehicle_types", {}),
                            density=record.get("density", 0),
                        )
                        db.add(traffic)
                        imported_count += 1
                    except json.JSONDecodeError:
                        logger.warning("跳过无效 JSON 行: %s...", line[:50])
                        continue
                    except ValueError as e:
                        logger.warning("跳过无效时间戳: %s", e)
                        continue

            db.commit()
            logger.info(
                "交通元数据导入完成: 共 %d 条，location_id=%s",
                imported_count,
                location_id,
            )
        except FileNotFoundError:
            # 文件不存在不应导致系统崩溃，记录日志并返回 0
            logger.error("JSONL 文件不存在: %s", jsonl_path)
            return 0
        except Exception:
            logger.exception("导入交通元数据时发生异常: %s", jsonl_path)
            db.rollback()
            return 0

        return imported_count

    def get_latest(self, db: Session, location_id: int) -> Optional[TrafficData]:
        """
        获取指定监测点最新一条交通数据

        按 timestamp 倒序取第一条，用于前端实时展示。
        """
        return (
            db.query(TrafficData)
            .filter(TrafficData.location_id == location_id)
            .order_by(TrafficData.timestamp.desc())
            .first()
        )

    def get_history(
        self, db: Session, location_id: int, limit: int = 24
    ):
        """
        获取指定监测点历史交通数据，按时间倒序，limit 条

        用于前端交通趋势图表展示。
        """
        return (
            db.query(TrafficData)
            .filter(TrafficData.location_id == location_id)
            .order_by(TrafficData.timestamp.desc())
            .limit(limit)
            .all()
        )


# 全局单例，其他模块直接 import 使用
traffic_service = TrafficService()