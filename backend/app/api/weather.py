"""
天气 API 路由

提供天气数据查询接口：
- GET /api/weather/latest  — 获取最新天气
- GET /api/weather/history — 获取历史天气
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import get_db
from app.services.weather_service import weather_service

router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.get("/latest")
def get_latest_weather(
    location_id: int = Query(..., description="监测点ID"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取指定监测点最新天气数据"""
    weather = weather_service.get_latest(db, location_id)
    if weather is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"监测点 {location_id} 暂无天气数据",
        )
    return {
        "id": weather.id,
        "location_id": weather.location_id,
        "timestamp": weather.timestamp,
        "temperature": weather.temperature,
        "humidity": weather.humidity,
        "precipitation": weather.precipitation,
        "wind_speed": weather.wind_speed,
        "visibility": weather.visibility,
        "weather_condition": weather.weather_condition,
    }


@router.get("/history")
def get_weather_history(
    location_id: int = Query(..., description="监测点ID"),
    limit: int = Query(24, ge=1, le=100, description="返回条数"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取指定监测点历史天气数据"""
    records = weather_service.get_history(db, location_id, limit)
    return [
        {
            "id": w.id,
            "location_id": w.location_id,
            "timestamp": w.timestamp,
            "temperature": w.temperature,
            "humidity": w.humidity,
            "precipitation": w.precipitation,
            "wind_speed": w.wind_speed,
            "visibility": w.visibility,
            "weather_condition": w.weather_condition,
        }
        for w in records
    ]