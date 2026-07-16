"""
管理员服务层
处理用户管理、模型管理等管理员业务逻辑
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session, selectinload
from app.entity.db_models import (
    User, UserRole, Role,
    ModelVersion, DetectionTask, DetectionResult,
    TrainingTask, TrainingMetric,
    ChatSession, ChatMessage,
    RefreshToken, OperationLog, FireAlert,
    DetectionScene,
)
from app.core.logger import get_logger

logger = get_logger(__name__)


class AdminService:
    """管理员服务"""

    # ────────────────────────────────────────────────
    # 用户管理
    # ────────────────────────────────────────────────

    def list_users(self, db: Session, skip: int = 0, limit: int = 50) -> list[dict]:
        """
        获取用户列表（分页）
        Args:
            db: 数据库会话
            skip: 跳过的记录数
            limit: 每页数量
        Returns:
            用户列表，每项包含角色信息
        """
        users = (
            db.query(User)
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
            .order_by(User.id.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        total = db.query(User).count()

        result = [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "phone": user.phone,
                "avatar": user.avatar,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "roles": [ur.role.name for ur in user.user_roles],
                "last_login_at": user.last_login_at,
                "created_at": user.created_at,
            }
            for user in users
        ]

        return {"total": total, "items": result}

    def toggle_user_status(self, db: Session, user_id: int, is_active: bool) -> dict:
        """
        启用/禁用用户
        Args:
            db: 数据库会话
            user_id: 用户 ID
            is_active: 目标状态
        Returns:
            更新后的用户信息
        Raises:
            HTTPException: 用户不存在
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        user.is_active = is_active
        db.commit()
        db.refresh(user)
        logger.info(f"管理员切换用户状态: user_id={user_id}, is_active={is_active}")
        return {"id": user.id, "username": user.username, "is_active": user.is_active}

    def delete_user(self, db: Session, user_id: int) -> dict:
        """
        删除用户（级联删除相关数据）
        删除顺序：
          1. fire_alerts（关联用户的 detection_tasks）
          2. detection_results（关联用户的 detection_tasks）
          3. detection_tasks
          4. training_metrics（关联用户的 training_tasks）
          5. model_versions（关联用户的 training_tasks）
          6. training_tasks
          7. chat_messages（关联用户的 chat_sessions）
          8. chat_sessions
          9. refresh_tokens
          10. operation_logs
          11. user_roles
          12. user
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        try:
            # 获取用户的检测任务 ID 列表
            task_ids = [
                t.id for t in
                db.query(DetectionTask.id).filter(DetectionTask.user_id == user_id).all()
            ]

            # 删除 fire_alerts
            if task_ids:
                db.query(FireAlert).filter(FireAlert.task_id.in_(task_ids)).delete(
                    synchronize_session=False
                )
                # 删除 detection_results
                db.query(DetectionResult).filter(DetectionResult.task_id.in_(task_ids)).delete(
                    synchronize_session=False
                )

            # 删除 detection_tasks
            db.query(DetectionTask).filter(DetectionTask.user_id == user_id).delete(
                synchronize_session=False
            )

            # 获取用户的训练任务 ID 列表
            training_ids = [
                t.id for t in
                db.query(TrainingTask.id).filter(TrainingTask.user_id == user_id).all()
            ]

            if training_ids:
                # 删除 training_metrics
                db.query(TrainingMetric).filter(TrainingMetric.task_id.in_(training_ids)).delete(
                    synchronize_session=False
                )
                # 删除 model_versions（关联训练任务的）
                db.query(ModelVersion).filter(ModelVersion.training_task_id.in_(training_ids)).delete(
                    synchronize_session=False
                )

            # 删除 training_tasks
            db.query(TrainingTask).filter(TrainingTask.user_id == user_id).delete(
                synchronize_session=False
            )

            # 获取用户的 chat_session ID 列表
            session_ids = [
                s.id for s in
                db.query(ChatSession.id).filter(ChatSession.user_id == user_id).all()
            ]

            if session_ids:
                # 删除 chat_messages
                db.query(ChatMessage).filter(ChatMessage.session_id.in_(session_ids)).delete(
                    synchronize_session=False
                )

            # 删除 chat_sessions
            db.query(ChatSession).filter(ChatSession.user_id == user_id).delete(
                synchronize_session=False
            )

            # 删除 refresh_tokens
            db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete(
                synchronize_session=False
            )

            # 删除 operation_logs
            db.query(OperationLog).filter(OperationLog.user_id == user_id).delete(
                synchronize_session=False
            )

            # 删除 user_roles
            db.query(UserRole).filter(UserRole.user_id == user_id).delete(
                synchronize_session=False
            )

            # 删除用户本身
            db.delete(user)
            db.commit()

            logger.info(f"管理员删除用户: user_id={user_id}, username={user.username}")
            return {"id": user_id, "message": "用户及其关联数据已删除"}

        except Exception as e:
            db.rollback()
            logger.error(f"删除用户失败: user_id={user_id}, error={e}")
            raise HTTPException(status_code=500, detail=f"删除用户失败: {str(e)}")

    # ────────────────────────────────────────────────
    # 模型管理
    # ────────────────────────────────────────────────

    def list_models(self, db: Session) -> list[dict]:
        """
        获取所有模型版本列表
        Returns:
            模型列表，包含场景名称
        """
        models = (
            db.query(ModelVersion, DetectionScene.display_name)
            .join(DetectionScene, DetectionScene.id == ModelVersion.scene_id)
            .order_by(ModelVersion.id.asc())
            .all()
        )

        result = []
        for model, scene_name in models:
            result.append({
                "id": model.id,
                "scene_id": model.scene_id,
                "scene_name": scene_name,
                "training_task_id": model.training_task_id,
                "version": model.version,
                "model_name": model.model_name,
                "model_type": model.model_type,
                "status": model.status,
                "map50": model.map50,
                "map50_95": model.map50_95,
                "is_default": model.is_default,
                "file_size": model.file_size,
                "created_at": model.created_at,
            })

        return result

    def toggle_model_status(self, db: Session, model_id: int, is_active: bool) -> dict:
        """
        切换模型状态
        Args:
            db: 数据库会话
            model_id: 模型版本 ID
            is_active: True 设为 active，False 设为 archived
        Returns:
            更新后的模型信息
        Raises:
            HTTPException: 模型不存在
        """
        model = db.query(ModelVersion).filter(ModelVersion.id == model_id).first()
        if not model:
            raise HTTPException(status_code=404, detail="模型版本不存在")

        model.status = "active" if is_active else "archived"
        db.commit()
        db.refresh(model)
        logger.info(f"管理员切换模型状态: model_id={model_id}, status={model.status}")
        return {"id": model.id, "model_name": model.model_name, "status": model.status}

    def delete_model(self, db: Session, model_id: int) -> dict:
        """
        删除模型版本
        - 将引用该模型的 detection_tasks 的 model_version_id 置为 NULL
        - 删除 MinIO 中的模型文件（如果有）
        """
        model = db.query(ModelVersion).filter(ModelVersion.id == model_id).first()
        if not model:
            raise HTTPException(status_code=404, detail="模型版本不存在")

        try:
            # 将引用此模型的检测任务的 model_version_id 置为 NULL
            db.query(DetectionTask).filter(DetectionTask.model_version_id == model_id).update(
                {"model_version_id": None}, synchronize_session=False
            )

            # 尝试删除 MinIO 中的模型文件
            if model.minio_url:
                try:
                    from app.storage.minio_client import MinIOClient
                    minio_client = MinIOClient()
                    # 从 URL 中提取 object_name（取最后一段路径）
                    object_name = model.minio_url.split("/")[-1]
                    minio_client.delete_file(object_name)
                except Exception as e:
                    logger.warning(f"删除 MinIO 模型文件失败（忽略）: {e}")

            model_name = model.model_name
            db.delete(model)
            db.commit()

            logger.info(f"管理员删除模型: model_id={model_id}, model_name={model_name}")
            return {"id": model_id, "message": "模型版本已删除"}

        except Exception as e:
            db.rollback()
            logger.error(f"删除模型失败: model_id={model_id}, error={e}")
            raise HTTPException(status_code=500, detail=f"删除模型失败: {str(e)}")


# 全局单例
admin_service = AdminService()
