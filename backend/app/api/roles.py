"""
RBAC 角色权限管理 API 路由

提供角色和权限的管理接口：
- GET  /api/roles                      — 角色列表
- POST /api/roles                      — 创建角色
- PUT  /api/roles/{role_id}            — 更新角色
- DELETE /api/roles/{role_id}          — 删除角色
- GET  /api/permissions                — 权限列表
- POST /api/roles/{role_id}/permissions — 给角色分配权限
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.session import get_db
from app.entity.db_models import UserRole, Role as RoleModel
from app.entity.schemas import RoleCreate, RoleResponse, PermissionResponse
from app.services.role_service import role_service

router = APIRouter(prefix="/api", tags=["roles"])


class RoleUpdate(BaseModel):
    """更新角色请求"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    permission_codes: Optional[list[str]] = None


class AssignPermissionsRequest(BaseModel):
    """分配权限请求"""
    permission_ids: list[int] = Field(..., description="权限 ID 列表")


@router.get("/roles")
def get_roles(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取所有角色列表"""
    roles = role_service.get_roles(db)
    return {"code": 200, "message": "success", "data": roles}


@router.post("/roles", status_code=status.HTTP_201_CREATED)
def create_role(
    role_data: RoleCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建新角色"""
    # 简单的管理员权限检查
    user_roles = db.query(UserRole).filter(UserRole.user_id == current_user.id).all()
    role_ids = [ur.role_id for ur in user_roles]
    has_admin = db.query(RoleModel).filter(RoleModel.id.in_(role_ids), RoleModel.name.in_(["admin", "system_admin"])).first()
    if not has_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    role = role_service.create_role(db, role_data.model_dump())
    perm_codes = role_data.permission_codes or []
    return {
        "code": 200,
        "message": "创建成功",
        "data": {
            "id": role.id,
            "name": role.name,
            "display_name": role.display_name,
            "description": role.description,
            "is_system": role.is_system,
            "permissions": perm_codes,
            "created_at": role.created_at,
        },
    }


@router.put("/roles/{role_id}")
def update_role(
    role_id: int,
    role_data: RoleUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新角色信息"""
    # 简单的管理员权限检查
    user_roles = db.query(UserRole).filter(UserRole.user_id == current_user.id).all()
    role_ids = [ur.role_id for ur in user_roles]
    has_admin = db.query(RoleModel).filter(RoleModel.id.in_(role_ids), RoleModel.name.in_(["admin", "system_admin"])).first()
    if not has_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    role = role_service.update_role(db, role_id, role_data.model_dump(exclude_unset=True))
    roles_list = role_service.get_roles(db)
    role_info = next((r for r in roles_list if r["id"] == role.id), None)
    return {"code": 200, "message": "更新成功", "data": role_info}


@router.delete("/roles/{role_id}")
def delete_role(
    role_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除角色（系统内置角色不可删除）"""
    # 简单的管理员权限检查
    user_roles = db.query(UserRole).filter(UserRole.user_id == current_user.id).all()
    role_ids = [ur.role_id for ur in user_roles]
    has_admin = db.query(RoleModel).filter(RoleModel.id.in_(role_ids), RoleModel.name.in_(["admin", "system_admin"])).first()
    if not has_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    role_service.delete_role(db, role_id)
    return {"code": 200, "message": "删除成功"}


@router.get("/permissions")
def get_permissions(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取所有权限列表"""
    permissions = role_service.get_permissions(db)
    data = [
        {
            "id": p.id,
            "code": p.code,
            "name": p.name,
            "module": p.module,
            "description": p.description,
        }
        for p in permissions
    ]
    return {"code": 200, "message": "success", "data": data}


@router.post("/roles/{role_id}/permissions")
def assign_permissions(
    role_id: int,
    request: AssignPermissionsRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """给角色分配权限（全量替换）"""
    # 简单的管理员权限检查
    user_roles = db.query(UserRole).filter(UserRole.user_id == current_user.id).all()
    role_ids = [ur.role_id for ur in user_roles]
    has_admin = db.query(RoleModel).filter(RoleModel.id.in_(role_ids), RoleModel.name.in_(["admin", "system_admin"])).first()
    if not has_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    role = role_service.assign_permissions(db, role_id, request.permission_ids)
    roles_list = role_service.get_roles(db)
    role_info = next((r for r in roles_list if r["id"] == role.id), None)
    return {"code": 200, "message": "权限分配成功", "data": role_info}
