"""
角色权限服务
处理 RBAC 角色/权限的 CRUD 业务逻辑
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.entity.db_models import Role, Permission, RolePermission
from app.core.logger import get_logger

logger = get_logger(__name__)


class RoleService:
    """角色权限服务"""

    def get_roles(self, db: Session) -> list[dict]:
        """
        获取所有角色（含权限编码列表）
        """
        roles = db.query(Role).options(
            joinedload(Role.role_permissions).joinedload(RolePermission.permission)
        ).order_by(Role.id).all()
        result = []
        for role in roles:
            perm_codes = [
                rp.permission.code
                for rp in role.role_permissions
                if rp.permission
            ]
            result.append({
                "id": role.id,
                "name": role.name,
                "display_name": role.display_name,
                "description": role.description,
                "is_system": role.is_system,
                "permissions": perm_codes,
                "created_at": role.created_at,
            })
        return result

    def create_role(self, db: Session, role_data: dict) -> Role:
        """
        创建角色
        Args:
            db: 数据库会话
            role_data: 包含 name, display_name, description, permission_codes
        Returns:
            新创建的角色对象
        Raises:
            HTTPException: 角色标识已存在
        """
        existing = db.query(Role).filter(Role.name == role_data["name"]).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"角色标识 '{role_data['name']}' 已存在")

        role = Role(
            name=role_data["name"],
            display_name=role_data["display_name"],
            description=role_data.get("description"),
        )
        db.add(role)
        db.flush()

        # 分配权限
        perm_codes = role_data.get("permission_codes", [])
        if perm_codes:
            self._assign_permission_codes(db, role.id, perm_codes)

        db.commit()
        db.refresh(role)
        logger.info(f"创建角色成功: {role.name} (id={role.id})")
        return role

    def update_role(self, db: Session, role_id: int, role_data: dict) -> Role:
        """
        更新角色信息
        """
        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise HTTPException(status_code=404, detail="角色不存在")

        if "display_name" in role_data and role_data["display_name"] is not None:
            role.display_name = role_data["display_name"]
        if "description" in role_data:
            role.description = role_data["description"]

        # 如果传了 permission_codes，重新分配权限
        if "permission_codes" in role_data and role_data["permission_codes"] is not None:
            # 清除旧权限
            db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
            self._assign_permission_codes(db, role_id, role_data["permission_codes"])

        db.commit()
        db.refresh(role)
        logger.info(f"更新角色成功: {role.name} (id={role.id})")
        return role

    def delete_role(self, db: Session, role_id: int) -> bool:
        """
        删除角色（系统内置角色不可删除）
        """
        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise HTTPException(status_code=404, detail="角色不存在")
        if role.is_system:
            raise HTTPException(status_code=400, detail="系统内置角色不可删除")

        db.delete(role)
        db.commit()
        logger.info(f"删除角色成功: {role.name} (id={role.id})")
        return True

    def get_permissions(self, db: Session) -> list[Permission]:
        """获取所有权限"""
        return db.query(Permission).order_by(Permission.module, Permission.id).all()

    def assign_permissions(self, db: Session, role_id: int, permission_ids: list[int]) -> Role:
        """
        给角色分配权限（全量替换）
        """
        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise HTTPException(status_code=404, detail="角色不存在")

        # 清除旧权限
        db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()

        # 添加新权限
        for perm_id in permission_ids:
            perm = db.query(Permission).filter(Permission.id == perm_id).first()
            if not perm:
                raise HTTPException(status_code=400, detail=f"权限 ID {perm_id} 不存在")
            rp = RolePermission(role_id=role_id, permission_id=perm_id)
            db.add(rp)

        db.commit()
        db.refresh(role)
        logger.info(f"角色 {role.name} 分配权限: {permission_ids}")
        return role

    def _assign_permission_codes(self, db: Session, role_id: int, codes: list[str]):
        """根据权限编码列表分配权限（内部方法）"""
        for code in codes:
            perm = db.query(Permission).filter(Permission.code == code).first()
            if perm:
                rp = RolePermission(role_id=role_id, permission_id=perm.id)
                db.add(rp)
            else:
                logger.warning(f"权限编码不存在，跳过: {code}")


# 全局单例
role_service = RoleService()
