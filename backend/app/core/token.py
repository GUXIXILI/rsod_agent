"""
Refresh Token 管理模块
提供 refresh_token 的生成、校验、撤销功能
独立模块 — 不修改 security.py，删除此文件即可移除 refresh_token 功能
"""
import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.config.settings import settings
from app.entity.db_models import User, RefreshToken


def create_refresh_token(db: Session, user: User) -> str:
    """
    为用户生成一个新的 refresh_token
    采用 Token Rotation 策略：每次刷新时旧 token 作废，发放新 token
    Args:
        db: 数据库会话
        user: 用户对象
    Returns:
        refresh_token 字符串
    """
    token_str = secrets.token_urlsafe(64)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    refresh_token = RefreshToken(
        user_id=user.id,
        token=token_str,
        expires_at=expires_at,
    )
    db.add(refresh_token)
    db.commit()
    return token_str


def validate_refresh_token(db: Session, token_str: str) -> User:
    """
    校验 refresh_token 并返回对应用户
    校验通过后自动撤销旧 token（Token Rotation）
    Args:
        db: 数据库会话
        token_str: refresh_token 字符串
    Returns:
        用户对象
    Raises:
        ValueError: token 无效或已过期
    """
    token_record = (
        db.query(RefreshToken)
        .filter(RefreshToken.token == token_str)
        .first()
    )

    if not token_record:
        raise ValueError("refresh_token 无效")

    if token_record.is_revoked:
        raise ValueError("refresh_token 已撤销")

    if token_record.expires_at < datetime.now(timezone.utc):
        db.delete(token_record)
        db.commit()
        raise ValueError("refresh_token 已过期")

    # Token Rotation：撤销旧 token
    token_record.is_revoked = True
    db.commit()

    # 获取用户
    user = db.query(User).filter(User.id == token_record.user_id).first()
    if not user:
        raise ValueError("用户不存在")

    return user


def revoke_refresh_token(db: Session, token_str: str):
    """
    撤销单个 refresh_token
    Args:
        db: 数据库会话
        token_str: refresh_token 字符串
    """
    token_record = (
        db.query(RefreshToken)
        .filter(RefreshToken.token == token_str)
        .first()
    )
    if token_record:
        token_record.is_revoked = True
        db.commit()


def revoke_all_user_tokens(db: Session, user_id: int):
    """
    撤销指定用户的所有 refresh_token（退出所有设备）
    Args:
        db: 数据库会话
        user_id: 用户 ID
    """
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.is_revoked == False,
    ).update({RefreshToken.is_revoked: True})
    db.commit()