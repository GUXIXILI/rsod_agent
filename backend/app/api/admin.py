"""
管理员 API 路由
- GET    /api/admin/users               用户列表（分页）
- PUT    /api/admin/users/{user_id}/status   启用/禁用用户
- DELETE /api/admin/users/{user_id}          删除用户
- GET    /api/admin/models              模型列表
- PUT    /api/admin/models/{model_id}/status  切换模型状态
- DELETE /api/admin/models/{model_id}        删除模型
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.core.deps import get_admin_user
from app.core.logger import get_logger
from app.entity.db_models import User
from app.entity.schemas import UserStatusRequest, ModelStatusRequest
from app.services.admin_service import admin_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ────────────────────────────────────────────────
# 用户管理
# ────────────────────────────────────────────────

@router.get("/users")
def list_users(
    skip: int = Query(default=0, ge=0, description="跳过记录数"),
    limit: int = Query(default=50, ge=1, le=200, description="每页数量"),
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """用户列表（分页），需要管理员权限"""
    data = admin_service.list_users(db, skip=skip, limit=limit)
    return {
        "code": 200,
        "message": "获取用户列表成功",
        "data": data,
    }


@router.put("/users/{user_id}/status")
def toggle_user_status(
    user_id: int,
    req: UserStatusRequest,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """启用/禁用用户，需要管理员权限"""
    # 不允许禁用自己
    if user_id == admin.id:
        return {"code": 400, "message": "不能修改自己的状态", "data": None}

    data = admin_service.toggle_user_status(db, user_id, req.is_active)
    return {
        "code": 200,
        "message": "用户状态已更新",
        "data": data,
    }


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """删除用户（级联删除相关数据），需要管理员权限"""
    # 不允许删除自己
    if user_id == admin.id:
        return {"code": 400, "message": "不能删除自己的账号", "data": None}

    data = admin_service.delete_user(db, user_id)
    return {
        "code": 200,
        "message": "用户已删除",
        "data": data,
    }


# ────────────────────────────────────────────────
# 模型管理
# ────────────────────────────────────────────────

@router.get("/models")
def list_models(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """模型版本列表，需要管理员权限"""
    data = admin_service.list_models(db)
    return {
        "code": 200,
        "message": "获取模型列表成功",
        "data": data,
    }


@router.put("/models/{model_id}/status")
def toggle_model_status(
    model_id: int,
    req: ModelStatusRequest,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """切换模型状态（active/archived），需要管理员权限"""
    data = admin_service.toggle_model_status(db, model_id, req.is_active)
    return {
        "code": 200,
        "message": "模型状态已更新",
        "data": data,
    }


@router.delete("/models/{model_id}")
def delete_model(
    model_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """删除模型版本，需要管理员权限"""
    data = admin_service.delete_model(db, model_id)
    return {
        "code": 200,
        "message": "模型已删除",
        "data": data,
    }
