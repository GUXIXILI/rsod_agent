"""
安全工具模块

提供应用安全核心功能：
- 密码哈希与校验：使用 bcrypt 算法，支持最长 72 字节密码
- JWT Token 生成与验证：使用 python-jose 库，支持 HS256 算法

安全注意事项：
- bcrypt 自动限制密码长度为 72 字节（算法内部限制）
- JWT 密钥通过 settings.JWT_SECRET_KEY 配置，生产环境必须使用强随机密钥
- Token 过期时间通过 settings.ACCESS_TOKEN_EXPIRE_MINUTES 配置
"""
from datetime import datetime, timedelta, timezone
from jose import jwt
import bcrypt
from app.config.settings import settings


def hash_password(password: str) -> str:
    """
    将明文密码加密为 bcrypt 哈希值。

    安全处理：
    - 自动截断超过 72 字节的密码（bcrypt 算法限制）
    - 使用随机生成的 salt 确保相同密码产生不同哈希值

    Args:
        password: 明文密码字符串

    Returns:
        str: bcrypt 哈希值字符串（60 字符）
    """
    max_length = 72
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > max_length:
        password_bytes = password_bytes[:max_length]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    校验明文密码与 bcrypt 哈希值是否匹配。

    同样自动截断超过 72 字节的密码，与 hash_password 保持一致。

    Args:
        plain_password: 用户输入的明文密码
        hashed_password: 数据库中存储的 bcrypt 哈希值

    Returns:
        bool: 密码是否匹配
    """
    max_length = 72
    password_bytes = plain_password.encode("utf-8")
    if len(password_bytes) > max_length:
        password_bytes = password_bytes[:max_length]
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))


def create_access_token(data: dict) -> str:
    """
    生成 JWT Access Token。

    Token 负载包含：
    - sub: 用户 ID（主题标识）
    - exp: 过期时间（UTC，由 settings.ACCESS_TOKEN_EXPIRE_MINUTES 决定）
    - 调用方传入的其他自定义字段

    签名算法使用 settings.JWT_ALGORITHM（默认 HS256），
    密钥使用 settings.JWT_SECRET_KEY。

    Args:
        data: Token 载荷数据，必须包含 {"sub": user_id}

    Returns:
        str: 编码后的 JWT Token 字符串
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    解析并验证 JWT Token。

    验证过程：
    1. 验证 Token 签名（使用 settings.JWT_SECRET_KEY）
    2. 验证 Token 是否过期（exp 字段）
    3. 验证算法类型（settings.JWT_ALGORITHM）

    注意：此函数不验证 Token 是否被撤销（refresh_token 机制)。

    Args:
        token: JWT Token 字符串（不含 "Bearer " 前缀）

    Returns:
        dict: Token 载荷数据（包含 sub、exp 等字段）

    Raises:
        JWTError: Token 无效、签名错误或已过期
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )