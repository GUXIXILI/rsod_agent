"""
全局配置模块
使用 pydantic-settings 管理所有配置项，支持从 .env 文件和环境变量读取
加载优先级：环境变量（系统级别）> .env 文件 > 代码中的默认值
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用全局配置"""

    # ── 应用基础配置 ──────────────────────────────────
    APP_NAME: str = "GLW RSOD Agent Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ── 数据库配置 ────────────────────────────────────
    DB_HOST: str = "localhost"
    DB_PORT: int = 5433
    DB_NAME: str = "rsod_agent"
    DB_USER: str = "rsod_admin"
    DB_PASSWORD: str = "rsod_admin"

    @property
    def DATABASE_URL(self) -> str:
        """构造 PostgreSQL 连接字符串"""
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # ── Redis 配置 ────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    @property
    def REDIS_URL(self) -> str:
        """构造 Redis 连接字符串"""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # ── MinIO 配置 ────────────────────────────────────
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "rsod-agent-images"
    MINIO_SECURE: bool = False

    # ── JWT 认证配置 ──────────────────────────────────
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── 登录安全配置 ──────────────────────────────────
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # ── 日志配置 ────────────────────────────────────
    LOG_DIR: str = "logs"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB，单日志文件最大大小
    LOG_BACKUP_COUNT: int = 5              # 保留 5 份历史日志备份

    # ── 训练配置 ──────────────────────────────────────
    TRAIN_OUTPUT_DIR: str = "runs/train"  # 训练输出目录（模型权重、日志等）
    DATASET_BASE_DIR: str = "datasets"    # 数据集根目录

    # Fire/smoke inference configuration
    FIRE_SMOKE_MODEL_PATH: str = (
        "runs/fire_smoke/yolo11n_e50_b16_s42/weights/best.pt"
    )
    FIRE_SMOKE_DEVICE: str = "0"
    FIRE_SMOKE_IMAGE_FIRE_THRESHOLD: float = 0.25
    FIRE_SMOKE_IMAGE_SMOKE_THRESHOLD: float = 0.20
    FIRE_SMOKE_VIDEO_FIRE_THRESHOLD: float = 0.20
    FIRE_SMOKE_VIDEO_SMOKE_THRESHOLD: float = 0.20
    FIRE_SMOKE_FIRE_CONFIRM_FRAMES: int = 3
    FIRE_SMOKE_SMOKE_CONFIRM_FRAMES: int = 3

    # ── 天气数据配置 ──────────────────────────────────
    WEATHER_API_KEY: str = ""             # 天气 API Key（可选，留空则使用模拟数据）
    WEATHER_API_PROVIDER: str = "pyowm"  # 天气 API 提供商：openweathermap/pyowm

    # ── 交通数据配置 ──────────────────────────────────
    TRAFFIC_API_KEY: str = ""             # 交通 API Key（可选）

    # ── 危险路况预测调度配置 ────────────────────────────
    SCHEDULER_ENABLED: bool = True        # 是否启用定时任务拉取天气数据

    # ── CORS 配置 ────────────────────────────────────
    ALLOWED_ORIGINS: str = (
        "http://localhost:3000,http://localhost:5173,http://localhost:8080"
    )

    @property
    def cors_origins_list(self) -> list:
        """将 CORS 配置字符串转为列表"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略 .env 中未在 Settings 中定义的字段


# 创建全局单例，其他模块直接 import 使用
settings = Settings()

# ── 安全配置校验 ──────────────────────────────────
# JWT_SECRET_KEY 是签发和验证 Token 的核心密钥，长度不足或为空会严重降低系统安全性。
# 这里在启动时进行检测并发出警告，提醒运维人员务必通过 .env 文件配置强密钥。
if not settings.JWT_SECRET_KEY or len(settings.JWT_SECRET_KEY) < 32:
    import warnings

    warnings.warn(
        "JWT_SECRET_KEY 未配置或长度不足 32 位，请立即在 .env 文件中设置强密钥，"
        "否则系统存在严重安全风险。",
        stacklevel=2,
    )
