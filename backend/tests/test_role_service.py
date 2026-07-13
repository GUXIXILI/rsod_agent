"""
角色权限服务（RBAC）单元测试
覆盖角色创建、角色列表、权限分配、角色删除、角色更新
"""
import pytest
from fastapi import HTTPException

from app.entity.db_models import Role, Permission, RolePermission
from app.services.role_service import RoleService, role_service


def _create_permission(db_session, code="detection:read", name="查看检测", module="detection"):
    perm = Permission(code=code, name=name, module=module)
    db_session.add(perm)
    db_session.commit()
    db_session.refresh(perm)
    return perm


class TestRoleCreate:
    """角色创建测试"""

    def test_create_role_success(self, db_session):
        """创建角色成功"""
        role = role_service.create_role(db_session, {
            "name": "test_operator",
            "display_name": "测试操作员",
            "description": "用于测试",
        })
        assert role.id is not None
        assert role.name == "test_operator"
        assert role.display_name == "测试操作员"

    def test_create_role_with_permissions(self, db_session):
        """创建角色并分配权限"""
        perm = _create_permission(db_session, code="test:read", name="测试读取", module="test")

        role = role_service.create_role(db_session, {
            "name": "test_viewer",
            "display_name": "测试访客",
            "permission_codes": ["test:read"],
        })
        assert role.id is not None

        # 验证权限关联
        rps = db_session.query(RolePermission).filter(RolePermission.role_id == role.id).all()
        assert len(rps) == 1
        assert rps[0].permission_id == perm.id

    def test_create_duplicate_role(self, db_session):
        """创建重复角色名抛出 HTTPException"""
        role_service.create_role(db_session, {
            "name": "dup_role",
            "display_name": "重复角色",
        })
        with pytest.raises(HTTPException) as exc_info:
            role_service.create_role(db_session, {
                "name": "dup_role",
                "display_name": "重复角色2",
            })
        assert exc_info.value.status_code == 400


class TestRoleList:
    """角色列表测试"""

    def test_get_roles_empty(self, db_session):
        """初始时角色列表为空"""
        roles = role_service.get_roles(db_session)
        # 可能已有系统内置角色，检查返回列表类型
        assert isinstance(roles, list)

    def test_get_roles_with_permissions(self, db_session):
        """角色列表包含权限编码"""
        perm = _create_permission(db_session, code="list:read", name="列表读取", module="list")
        role = role_service.create_role(db_session, {
            "name": "list_role",
            "display_name": "列表角色",
            "permission_codes": ["list:read"],
        })

        roles = role_service.get_roles(db_session)
        found = next((r for r in roles if r["name"] == "list_role"), None)
        assert found is not None
        assert "list:read" in found["permissions"]


class TestRolePermissionAssign:
    """权限分配测试"""

    def test_assign_permissions_by_id(self, db_session):
        """按权限 ID 分配权限"""
        role = role_service.create_role(db_session, {
            "name": "perm_assign",
            "display_name": "权限分配角色",
        })
        perm = _create_permission(db_session, code="assign:write", name="分配写入", module="assign")

        updated_role = role_service.assign_permissions(db_session, role.id, [perm.id])
        assert updated_role is not None

        rps = db_session.query(RolePermission).filter(RolePermission.role_id == role.id).all()
        assert len(rps) == 1

    def test_assign_permissions_replaces_old(self, db_session):
        """分配权限全量替换旧权限"""
        perm1 = _create_permission(db_session, code="old:read", name="旧读取", module="old")
        perm2 = _create_permission(db_session, code="new:read", name="新读取", module="new")

        role = role_service.create_role(db_session, {
            "name": "replace_perm",
            "display_name": "替换权限角色",
            "permission_codes": ["old:read"],
        })

        role_service.assign_permissions(db_session, role.id, [perm2.id])
        rps = db_session.query(RolePermission).filter(RolePermission.role_id == role.id).all()
        assert len(rps) == 1
        assert rps[0].permission_id == perm2.id

    def test_assign_invalid_permission_id(self, db_session):
        """分配不存在的权限 ID 抛出 HTTPException"""
        role = role_service.create_role(db_session, {
            "name": "invalid_perm",
            "display_name": "无效权限角色",
        })
        with pytest.raises(HTTPException) as exc_info:
            role_service.assign_permissions(db_session, role.id, [9999])
        assert exc_info.value.status_code == 400

    def test_assign_permissions_nonexistent_role(self, db_session):
        """给不存在的角色分配权限抛出 HTTPException"""
        with pytest.raises(HTTPException) as exc_info:
            role_service.assign_permissions(db_session, 9999, [])
        assert exc_info.value.status_code == 404


class TestRoleDelete:
    """角色删除测试"""

    def test_delete_role_success(self, db_session):
        """删除非系统角色成功"""
        role = role_service.create_role(db_session, {
            "name": "to_delete",
            "display_name": "待删除角色",
        })
        result = role_service.delete_role(db_session, role.id)
        assert result is True

    def test_delete_system_role_fails(self, db_session):
        """系统内置角色不可删除"""
        role = Role(name="system_admin", display_name="系统管理员", is_system=True)
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)

        with pytest.raises(HTTPException) as exc_info:
            role_service.delete_role(db_session, role.id)
        assert exc_info.value.status_code == 400

    def test_delete_nonexistent_role(self, db_session):
        """删除不存在的角色抛出 HTTPException"""
        with pytest.raises(HTTPException) as exc_info:
            role_service.delete_role(db_session, 9999)
        assert exc_info.value.status_code == 404


class TestRoleUpdate:
    """角色更新测试"""

    def test_update_role_display_name(self, db_session):
        """更新角色显示名称"""
        role = role_service.create_role(db_session, {
            "name": "update_me",
            "display_name": "旧名称",
        })
        updated = role_service.update_role(db_session, role.id, {"display_name": "新名称"})
        assert updated.display_name == "新名称"

    def test_update_nonexistent_role(self, db_session):
        """更新不存在的角色抛出 HTTPException"""
        with pytest.raises(HTTPException) as exc_info:
            role_service.update_role(db_session, 9999, {"display_name": "x"})
        assert exc_info.value.status_code == 404


class TestGetPermissions:
    """获取权限列表测试"""

    def test_get_permissions(self, db_session):
        """获取所有权限列表"""
        _create_permission(db_session, code="get:test1", name="测试1", module="get")
        _create_permission(db_session, code="get:test2", name="测试2", module="get")

        perms = role_service.get_permissions(db_session)
        assert isinstance(perms, list)
        codes = [p.code for p in perms]
        assert "get:test1" in codes
        assert "get:test2" in codes


class TestJoinedLoadOptimization:
    """验证 joinedload 后 get_roles 返回结果正确（权限列表非空）"""

    def test_get_roles_joinedload_permissions_nonempty(self, db_session):
        """角色关联多个权限时，joinedload 返回完整权限列表"""
        p1 = _create_permission(db_session, code="jl:read", name="读取", module="jl")
        p2 = _create_permission(db_session, code="jl:write", name="写入", module="jl")
        p3 = _create_permission(db_session, code="jl:delete", name="删除", module="jl")

        role_service.create_role(db_session, {
            "name": "jl_role",
            "display_name": "joinedload测试角色",
            "permission_codes": ["jl:read", "jl:write", "jl:delete"],
        })

        roles = role_service.get_roles(db_session)
        found = next((r for r in roles if r["name"] == "jl_role"), None)
        assert found is not None
        assert len(found["permissions"]) == 3
        assert "jl:read" in found["permissions"]
        assert "jl:write" in found["permissions"]
        assert "jl:delete" in found["permissions"]

    def test_get_roles_joinedload_no_permissions(self, db_session):
        """无权限的角色，joinedload 返回空权限列表"""
        role_service.create_role(db_session, {
            "name": "jl_empty",
            "display_name": "无权限角色",
        })

        roles = role_service.get_roles(db_session)
        found = next((r for r in roles if r["name"] == "jl_empty"), None)
        assert found is not None
        assert found["permissions"] == []
