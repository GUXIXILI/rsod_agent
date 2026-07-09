"""
交通 API 路由

提供交通数据查询接口：
- GET /api/traffic/latest  — 获取最新交通数据
- GET /api/traffic/history — 获取历史交通数据
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import get_db
from app.services.traffic_service import traffic_service

router = APIRouter(prefix="/api/traffic", tags=["traffic"])


@router.get("/latest")
def get_latest_traffic(
    location_id: int = Query(..., description="监测点ID"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取指定监测点最新交通数据"""
    traffic = traffic_service.get_latest(db, location_id)
    if traffic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"监测点 {location_id} 暂无交通数据",
        )
    return {
        "id": traffic.id,
        "location_id": traffic.location_id,
        "timestamp": traffic.timestamp,
        "vehicle_count": traffic.vehicle_count,
        "avg_speed": traffic.avg_speed,
        "vehicle_types": traffic.vehicle_types,
        "density": traffic.density,
    }


@router.get("/history")
def get_traffic_history(
    location_id: int = Query(..., description="监测点ID"),
    limit: int = Query(24, ge=1, le=100, description="返回条数"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取指定监测点历史交通数据"""
    records = traffic_service.get_history(db, location_id, limit)
    return [
        {
            "id": t.id,
            "location_id": t.location_id,
            "timestamp": t.timestamp,
            "vehicle_count": t.vehicle_count,
            "avg_speed": t.avg_speed,
            "vehicle_types": t.vehicle_types,
            "density": t.density,
        }
        for t in records
    ]