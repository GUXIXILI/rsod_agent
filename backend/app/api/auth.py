"""
认证相关 API 路由
- POST /api/auth/register  用户注册
- POST /api/auth/login     用户登录
- POST /api/auth/refresh   刷新 access_token
- POST /api/auth/logout    退出登录（撤销 refresh_token）
- POST /api/auth/logout-all  退出所有设备
- GET  /api/auth/me        获取当前用户信息
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session
from app.core.rate_limit import check_login_rate_limit, record_login_failure, clear_login_attempts
from app.core.security import decode_access_token, create_access_token
from app.core.token import create_refresh_token, validate_refresh_token, revoke_refresh_token, revoke_all_user_tokens
from app.core.logger import get_logger
from app.config.settings import settings
from app.database.session import get_db
from app.entity.schemas import (
    TokenResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    UserUpdate,
    ChangePassword,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.services.user_service import user_service

logger = get_logger(__name__)


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
    user.last_login_at = datetime.now(timezone.utc)
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


# ══════════════════════════════════════════════════════════════
# 密码重置（公开端点，无需认证）
# ══════════════════════════════════════════════════════════════

@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    忘记密码 — 生成重置令牌
    - 开发阶段直接返回 token，生产环境应改为发送邮件
    """
    token = user_service.create_reset_token(db, req.email)
    return {"code": 200, "message": "重置令牌已生成", "data": {"token": token}}


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    重置密码 — 使用令牌重置
    - 令牌有效期 1 小时，使用后立即失效
    """
    success = user_service.reset_password(db, req.token, req.new_password)
    if success:
        return {"code": 200, "message": "密码重置成功"}
    return {"code": 400, "message": "令牌无效或已过期"}


# ══════════════════════════════════════════════════════════════
# 用户信息修改（需要认证）
# ══════════════════════════════════════════════════════════════

ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2MB


@router.put("/profile")
async def update_profile(
    req: UserUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改个人信息（邮箱、手机号）"""
    user = user_service.update_profile(db, current_user.id, email=req.email, phone=req.phone)
    return {
        "code": 200,
        "message": "个人信息已更新",
        "data": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "phone": user.phone,
            "avatar": user.avatar,
        },
    }


@router.put("/password")
async def change_password(
    req: ChangePassword,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改密码（需验证旧密码）"""
    success = user_service.change_password(db, current_user.id, req.old_password, req.new_password)
    if not success:
        return {"code": 400, "message": "旧密码错误", "data": None}
    return {"code": 200, "message": "密码修改成功", "data": None}


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    上传头像到 MinIO avatars bucket
    - 文件大小 ≤ 2MB
    - 支持格式：jpg/png/gif/webp
    """
    # 校验文件类型
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {file.content_type}，仅支持 jpg/png/gif/webp",
        )

    # 读取文件并校验大小
    file_bytes = await file.read()
    if len(file_bytes) > MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制（最大 2MB），当前 {len(file_bytes) / 1024 / 1024:.2f}MB",
        )

    url = user_service.upload_avatar(
        db, current_user.id, file_bytes, file.filename, file.content_type
    )
    logger.info(f"头像上传成功: user_id={current_user.id}")
    return {"code": 200, "message": "头像上传成功", "data": {"avatar_url": url}}