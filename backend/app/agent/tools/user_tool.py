"""
用户查询工具封装模块

封装用户列表查询工具，供 ReAct Agent 在推理过程中调用。

提供工具：
- query_user_list：查询系统用户列表
"""

import json

from langchain_core.tools import tool

from app.database.session import SessionLocal
from app.entity.db_models import User
from app.core.logger import get_logger

logger = get_logger(__name__)


@tool
def query_user_list() -> str:
    """查询系统用户列表。

    返回系统中所有活跃用户的基本信息，包括用户名、邮箱、角色等。

    适用场景：
    - 管理员需要查看系统中有哪些用户。
    - 需要了解用户角色分配情况。

    Returns:
        str: 格式化的用户列表信息。
    """
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active == True).order_by(User.id).all()

        if not users:
            return json.dumps({"tool": "query_user_list", "status": "success", "summary": "当前系统中没有活跃用户", "data": {"total": 0, "users": []}}, ensure_ascii=False)

        result = {
            "tool": "query_user_list",
            "status": "success",
            "summary": f"共找到 {len(users)} 个活跃用户",
            "data": {
                "total": len(users),
                "users": [
                    {
                        "username": user.username,
                        "email": user.email,
                        "roles": [ur.role.name for ur in user.user_roles] if user.user_roles else [],
                        "is_superuser": user.is_superuser,
                        "last_login_at": str(user.last_login_at)[:19] if user.last_login_at else None,
                    }
                    for user in users
                ]
            }
        }
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        logger.exception("用户查询工具调用失败")
        return json.dumps({"tool": "query_user_list", "status": "error", "summary": f"用户查询失败：{str(e)}", "data": None}, ensure_ascii=False, default=str)
    finally:
        db.close()