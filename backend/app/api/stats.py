"""
数据看板 API 路由

提供检测统计数据查询接口：
- GET /api/stats/overview — 总览统计
- GET /api/stats/fire-level-distribution — 火情等级分布
- GET /api/stats/trend — 检测趋势
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import get_db
from app.services.stats_service import stats_service

router = APIRouter(tags=["stats"])


@router.get("/overview")
def get_overview(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取总览统计数据"""
    result = stats_service.get_overview(db, current_user.id)
    return {"code": 200, "message": "success", "data": result}


@router.get("/fire-level-distribution")
@router.get("/fire-dist")
def get_fire_level_distribution(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取火情等级分布"""
    result = stats_service.get_fire_level_distribution(db, current_user.id)
    return {"code": 200, "message": "success", "data": result}


@router.get("/trend")
def get_trend(
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取检测趋势"""
    result = stats_service.get_trend(db, current_user.id, days=days)
    return {"code": 200, "message": "success", "data": result}


@router.get("/class-dist")
def get_class_distribution(
    days: int = Query(30, ge=1, le=365),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取类别分布统计"""
    result = stats_service.get_class_distribution(db, current_user.id, days=days)
    return {"code": 200, "message": "success", "data": result}


@router.get("/scene-dist")
def get_scene_distribution(
    days: int = Query(30, ge=1, le=365),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取场景分布统计"""
    result = stats_service.get_scene_distribution(db, current_user.id, days=days)
    return {"code": 200, "message": "success", "data": result}


@router.get("/type-dist")
def get_type_distribution(
    days: int = Query(30, ge=1, le=365),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取任务类型分布统计"""
    result = stats_service.get_type_distribution(db, current_user.id, days=days)
    return {"code": 200, "message": "success", "data": result}