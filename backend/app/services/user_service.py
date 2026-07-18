"""
用户服务层
处理用户注册、登录、鉴权、密码重置、个人资料修改等业务逻辑
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.core.logger import get_logger
from app.core.security import create_access_token, hash_password, verify_password
from app.entity.db_models import User, PasswordResetToken

logger = get_logger(__name__)


class UserService:
    """用户服务"""

    @staticmethod
    def register(db: Session, username: str, email: str, password: str) -> User:
        """
        用户注册
        Args:
            db: 数据库会话
            username: 用户名
            email: 邮箱
            password: 明文密码
        Returns:
            新创建的用户对象
        Raises:
            HTTPException: 用户名或邮箱已存在
        """
        # 检查用户名是否已存在
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="用户名已存在")

        # 检查邮箱是否已存在
        existing_email = db.query(User).filter(User.email == email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="邮箱已被注册")

        # 创建新用户
        new_user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    @staticmethod
    def login(db: Session, identifier: str, password: str) -> User:
        """
        用户登录（支持用户名或邮箱）
        使用 SQLAlchemy OR 查询，先查用户名再查邮箱，避免暴露具体错误类型
        Args:
            db: 数据库会话
            identifier: 用户名或邮箱
            password: 明文密码
        Returns:
            登录成功的用户对象
        Raises:
            HTTPException: 用户名或密码错误（不区分具体是用户名错还是邮箱错）
        """
        # 使用 OR 查询，同时匹配用户名或邮箱
        user = db.query(User).filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()
        if not user:
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        if not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        return user

    @staticmethod
    def create_access_token_for_user(user: User) -> str:
        """为用户生成 JWT Token"""
        return create_access_token(data={"sub": str(user.id)})

    @staticmethod
    def get_user_roles(db: Session, user: User) -> list[str]:
        """获取用户的角色标识列表"""
        return [ur.role.name for ur in user.user_roles]

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User:
        """根据 ID 获取用户"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        return user

    # ══════════════════════════════════════════════════════════════
    # 密码重置
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def create_reset_token(db: Session, email: str) -> str:
        """
        创建密码重置令牌，返回明文令牌（仅返回一次）
        """
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="该邮箱未注册")

        plain_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(plain_token.encode()).hexdigest()

        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(reset_token)
        db.commit()
        logger.info(f"密码重置令牌已生成: user_id={user.id}")
        return plain_token

    @staticmethod
    def reset_password(db: Session, token: str, new_password: str) -> bool:
        """
        使用令牌重置密码
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        now = datetime.now(timezone.utc)

        reset_token = db.query(PasswordResetToken).filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used == False,
            PasswordResetToken.expires_at > now,
        ).first()

        if not reset_token:
            return False

        user = db.query(User).filter(User.id == reset_token.user_id).first()
        if not user:
            return False

        user.hashed_password = hash_password(new_password)
        reset_token.used = True
        db.commit()
        logger.info(f"密码已重置: user_id={user.id}")
        return True

    # ══════════════════════════════════════════════════════════════
    # 用户信息修改
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def update_profile(db: Session, user_id: int, email: str = None, phone: str = None) -> User:
        """更新用户个人信息"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        if email and email != user.email:
            existing = db.query(User).filter(
                User.email == email,
                User.id != user_id,
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="该邮箱已被其他用户使用")
            user.email = email

        if phone is not None:
            user.phone = phone

        db.commit()
        db.refresh(user)
        logger.info(f"用户信息已更新: user_id={user_id}")
        return user

    @staticmethod
    def change_password(db: Session, user_id: int, old_password: str, new_password: str) -> bool:
        """修改密码（需验证旧密码）"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        if not verify_password(old_password, user.hashed_password):
            return False

        user.hashed_password = hash_password(new_password)
        db.commit()
        logger.info(f"用户密码已修改: user_id={user_id}")
        return True

    @staticmethod
    def upload_avatar(db: Session, user_id: int, file_bytes: bytes, filename: str, content_type: str) -> str:
        """上传头像到 MinIO avatars bucket"""
        from app.storage.minio_client import MinIOClient

        ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
        object_name = f"avatars/{user_id}/{uuid.uuid4()}.{ext}"

        minio_client = MinIOClient()
        url = minio_client.upload_bytes(object_name, file_bytes, content_type)

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        user.avatar = url
        db.commit()
        logger.info(f"头像已上传: user_id={user_id}, object={object_name}")
        return url


# 全局单例
user_service = UserService()