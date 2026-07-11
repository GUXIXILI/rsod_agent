"""
场景 API 路由

提供检测场景管理接口：
- GET /api/scenes — 获取活跃场景列表（训练任务下拉框使用）
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import get_db
from app.entity.db_models import DetectionScene

router = APIRouter(prefix="/api/scenes", tags=["scenes"])


@router.get("")
def get_active_scenes(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取所有活跃检测场景列表

    返回字段包含前端训练页面所需的 id、name、display_name、class_names 等。
    """
    scenes = (
        db.query(DetectionScene)
        .filter(DetectionScene.is_active == True)
        .order_by(DetectionScene.created_at.desc())
        .all()
    )

    return [
        {
            "id": scene.id,
            "name": scene.name,
            "display_name": scene.display_name,
            "description": scene.description,
            "category": scene.category,
            "class_names": scene.class_names,
            "class_names_cn": scene.class_names_cn,
            "is_active": scene.is_active,
            "location_type": scene.location_type,
            "address": scene.address,
            "camera_count": scene.camera_count,
            "created_at": scene.created_at,
        }
        for scene in scenes
    ]
