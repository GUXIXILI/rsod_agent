"""
公共依赖注入函数
用于 API 路由中的权限校验和用户认证
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.api.auth import get_current_user
from app.entity.db_models import User, UserRole, Role


def get_admin_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """
    验证当前用户是否为管理员
    判断逻辑：
      1. is_superuser 字段为 True，直接放行
      2. 否则查询用户角色，角色 name 为 'admin' 则放行
      3. 都不满足则返回 403
    """
    # 超级管理员直接通过
    if getattr(current_user, "is_superuser", False):
        return current_user

    # 查询用户角色列表
    user_roles = (
        db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == current_user.id)
        .all()
    )
    role_names = [r.name for r in user_roles]

    if "admin" not in role_names:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )

    return current_user
