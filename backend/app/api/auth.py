"""
认证相关 API 路由
- POST /api/auth/register  用户注册
- POST /api/auth/login     用户登录
- POST /api/auth/refresh   刷新 access_token
- POST /api/auth/logout    退出登录（撤销 refresh_token）
- POST /api/auth/logout-all  退出所有设备
- GET  /api/auth/me        获取当前用户信息
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session
from app.core.rate_limit import check_login_rate_limit, record_login_failure, clear_login_attempts
from app.core.security import decode_access_token, create_access_token
from app.core.token import create_refresh_token, validate_refresh_token, revoke_refresh_token, revoke_all_user_tokens
from app.config.settings import settings
from app.database.session import get_db
from app.entity.schemas import (
    TokenResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.user_service import user_service


router = APIRouter(prefix="/api/auth", tags=["认证"])

# OAuth2 密码模式，用于从请求 Header 中提取 Token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    从 JWT Token 中解析当前用户
    在需要认证的路由中通过 Depends(get_current_user) 使用
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    user = user_service.get_user_by_id(db, user_id)
    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: UserRegister, db: Session = Depends(get_db)):
    """
    用户注册
    - **username**: 用户名（3-50 字符）
    - **email**: 邮箱
    - **password**: 密码（至少 6 位）
    """
    user = user_service.register(
        db=db,
        username=request.username,
        email=request.email,
        password=request.password,
    )
    return user


@router.post("/login", response_model=TokenResponse)
async def login(request: UserLogin, db: Session = Depends(get_db)):
    """
    用户登录
    - 返回 JWT access_token + refresh_token
    - 后续请求在 Header 中携带：Authorization: Bearer <token>
    """
    # 登录速率限制检查
    is_locked, remaining = check_login_rate_limit(request.username)
    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"登录失败次数过多，请 {settings.LOGIN_LOCKOUT_MINUTES} 分钟后再试",
        )

    try:
        user = user_service.login(
            db=db,
            identifier=request.username,
            password=request.password,
        )
    except HTTPException:
        # 登录失败，记录计数
        record_login_failure(request.username)
        raise

    # 登录成功，清除失败计数
    clear_login_attempts(request.username)

    # 更新最后登录时间
    user.last_login_at = datetime.utcnow()
    db.commit()

    # 生成 Token
    access_token = user_service.create_access_token_for_user(user)
    refresh_token = create_refresh_token(db, user)
    roles = user_service.get_user_roles(db, user)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "avatar": user.avatar,
            "roles": roles,
        },
    }


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh(
    request: TokenRefreshRequest,
    db: Session = Depends(get_db),
):
    """
    刷新 access_token
    - 使用 refresh_token 获取新的 access_token 和新的 refresh_token
    - 旧 refresh_token 会被立即撤销，防止盗用
    """
    try:
        user = validate_refresh_token(db, request.refresh_token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    # 生成新的 access_token 和新的 refresh_token（Token Rotation）
    access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(db, user)

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.post("/logout")
async def logout(
    request: TokenRefreshRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """退出当前登录：撤销当前 refresh_token"""
    revoke_refresh_token(db, request.refresh_token)
    return {"detail": "退出成功"}


@router.post("/logout-all")
async def logout_all_devices(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """退出所有设备：撤销当前用户的所有 refresh_token"""
    revoke_all_user_tokens(db, current_user.id)
    return {"detail": "所有设备已退出登录"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前登录用户信息（需要 Token 认证）"""
    roles = user_service.get_user_roles(db, current_user)
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "phone": current_user.phone,
        "avatar": current_user.avatar,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "roles": roles,
        "last_login_at": current_user.last_login_at,
        "created_at": current_user.created_at,
    }