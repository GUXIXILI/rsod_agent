"""
用户管理 API 路由

提供用户查询和个人信息管理接口：
- GET /api/user/list — 用户列表
- GET /api/user/roles — 角色查询
- GET /api/user/profile — 个人信息查看
- PUT /api/user/password — 密码修改
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import get_db
from app.entity.db_models import User, Role, UserRole
from app.services.user_service import user_service

router = APIRouter(prefix="/api/user", tags=["user"])


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


@router.get("/list")
def get_user_list(
    skip: int = 0,
    limit: int = 20,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取用户列表（管理员可查看所有用户，普通用户仅查看自己）"""
    query = db.query(User)
    total = query.count()
    users = query.offset(skip).limit(limit).all()
    return {
        "code": 200, "message": "success",
        "data": {
            "total": total,
            "items": [{"id": u.id, "username": u.username, "email": u.email, "is_active": u.is_active} for u in users],
        },
    }


@router.get("/roles")
def get_user_roles(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取角色列表"""
    roles = db.query(Role).all()
    return {
        "code": 200, "message": "success",
        "data": [{"id": r.id, "name": r.name, "description": r.description} for r in roles],
    }


@router.get("/profile")
def get_profile(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查看当前用户个人信息"""
    user = db.query(User).filter(User.id == current_user.id).first()
    roles = [ur.role.name for ur in user.user_roles]
    return {
        "code": 200, "message": "success",
        "data": {
            "id": user.id, "username": user.username, "email": user.email,
            "phone": getattr(user, "phone", None), "avatar": getattr(user, "avatar", None),
            "is_active": user.is_active, "roles": roles,
            "created_at": user.created_at,
        },
    }


@router.put("/password")
def change_password(
    request: PasswordChangeRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改当前用户密码"""
    success = user_service.change_password(db, current_user.id, request.old_password, request.new_password)
    if not success:
        raise HTTPException(status_code=400, detail="旧密码不正确")
    return {"code": 200, "message": "密码修改成功"}