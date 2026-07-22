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
from app.entity.db_models import User, Role, UserRole, UserConfig
from app.services.user_service import user_service
from typing import Optional

router = APIRouter(prefix="/api/user", tags=["user"])


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


class ProfileUpdateRequest(BaseModel):
    nickname: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class ConfigUpdateRequest(BaseModel):
    agent_mode: str  # "single" 或 "multi"


@router.get("/list")
def get_user_list(
    page: int = 1,
    page_size: int = 20,
    skip: int = 0,
    limit: int = 20,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取用户列表（管理员可查看所有用户，普通用户仅查看自己）

    支持两种分页方式：
    - page + page_size：前端常用（page 从 1 开始）
    - skip + limit：兼容旧接口
    优先使用 page+page_size，若 page>1 则覆盖 skip 计算
    """
    # 前端使用 page+page_size 时，自动计算 skip 并覆盖 limit
    if page > 1 or page_size != 20:
        skip = (page - 1) * page_size
        limit = page_size
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
            "id": user.id, "username": user.username, "nickname": user.nickname,
            "email": user.email,
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


@router.put("/profile")
def update_profile(
    request: ProfileUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新当前用户个人资料（昵称、电话、邮箱）"""
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if request.nickname is not None:
        user.nickname = request.nickname
    if request.phone is not None:
        user.phone = request.phone
    if request.email is not None:
        # 检查邮箱是否被其他用户占用
        if request.email != user.email:
            existing = db.query(User).filter(User.email == request.email, User.id != user.id).first()
            if existing:
                raise HTTPException(status_code=400, detail="该邮箱已被其他用户使用")
        user.email = request.email

    db.commit()
    db.refresh(user)

    roles = [ur.role.name for ur in user.user_roles]
    return {
        "code": 200, "message": "个人资料更新成功",
        "data": {
            "id": user.id, "username": user.username, "email": user.email,
            "nickname": getattr(user, "nickname", None),
            "phone": getattr(user, "phone", None),
            "avatar": getattr(user, "avatar", None),
            "is_active": user.is_active, "roles": roles,
            "created_at": user.created_at,
        },
    }


@router.get("/config")
def get_user_config(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的 Agent 模式配置，不存在时自动创建默认值（single）"""
    config = db.query(UserConfig).filter(UserConfig.user_id == current_user.id).first()
    if not config:
        config = UserConfig(user_id=current_user.id, agent_mode="single")
        db.add(config)
        db.commit()
        db.refresh(config)
    return {
        "code": 200,
        "message": "success",
        "data": {
            "agent_mode": config.agent_mode,
        },
    }


@router.put("/config")
def update_user_config(
    request: ConfigUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新当前用户的 Agent 模式配置（仅接受 single 或 multi）"""
    if request.agent_mode not in ("single", "multi"):
        raise HTTPException(status_code=400, detail="agent_mode 必须为 single 或 multi")

    config = db.query(UserConfig).filter(UserConfig.user_id == current_user.id).first()
    if not config:
        config = UserConfig(user_id=current_user.id, agent_mode=request.agent_mode)
        db.add(config)
    else:
        config.agent_mode = request.agent_mode
    db.commit()
    db.refresh(config)
    return {
        "code": 200,
        "message": "Agent 模式已切换",
        "data": {
            "agent_mode": config.agent_mode,
        },
    }