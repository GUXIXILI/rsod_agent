"""
全局配置模块
使用 pydantic-settings 管理所有配置项，支持从 .env 文件和环境变量读取
加载优先级：环境变量（系统级别）> .env 文件 > 代码中的默认值
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用全局配置"""

    # ── 应用基础配置 ──────────────────────────────────
    APP_NAME: str = "Fire & Smoke Detection Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ── 数据库配置 ────────────────────────────────────
    DB_HOST: str = "localhost"
    DB_PORT: int = 5433
    DB_NAME: str = "rsod_agent"
    DB_USER: str = "rsod_admin"
    DB_PASSWORD: str = ""

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
    REDIS_DB: int = 0

    @property
    def REDIS_URL(self) -> str:
        """构造 Redis 连接字符串"""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # ── MinIO 配置 ────────────────────────────────────
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET: str = "fire-detection-images"
    MINIO_SECURE: bool = False

    # ── LLM 配置 ──────────────────────────────────────
    LLM_STUB_MODE: bool = True
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_MODEL: str = "qwen-plus"
    USE_LOCAL_LLM: bool = False
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"

    # ── RAG / Embedding 配置 ───────────────────────────
    # 向量化模型名称，支持 openai 或 qwen（通义千问）系列
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    # OpenAI API Key（占位值，实际使用时需配置）
    OPENAI_API_KEY: str = ""
    # 通义千问 API Key（占位值，实际使用时需配置）
    QWEN_API_KEY: str = ""

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
    DEFAULT_MODEL_PATH: str = ""          # 默认模型权重路径（为空时使用 YOLOv11n 默认权重）

    # ── ZIP 检测配置 ──────────────────────────────────
    ZIP_MAX_SIZE_MB: int = 200       # ZIP 解压后最大总大小（MB）
    ZIP_MAX_IMAGES: int = 100        # ZIP 中最多处理的图片数量

    # Fire/smoke inference configuration
    FIRE_SMOKE_MODEL_PATH: str = "runs/train/54/d63a63d7-e43b-4eee-a70b-7e9df0ed8f1a/train/weights/best.pt"
    FIRE_SMOKE_DEVICE: str = "0"
    FIRE_SMOKE_IMAGE_FIRE_THRESHOLD: float = 0.25
    FIRE_SMOKE_IMAGE_SMOKE_THRESHOLD: float = 0.20
    FIRE_SMOKE_VIDEO_FIRE_THRESHOLD: float = 0.20
    FIRE_SMOKE_VIDEO_SMOKE_THRESHOLD: float = 0.20
    FIRE_SMOKE_FIRE_CONFIRM_FRAMES: int = 3
    FIRE_SMOKE_SMOKE_CONFIRM_FRAMES: int = 3

    # ── 定时任务配置 ──────────────────────────────────
    SCHEDULER_ENABLED: bool = False       # 是否启用定时任务（如定时清理过期检测记录）

    # ── WebSocket 配置 ───────────────────────────────
    WEBSOCKET_MAX_CONNECTIONS: int = 10   # WebSocket 最大并发连接数
    WEBSOCKET_IDLE_TIMEOUT: int = 60      # WebSocket 空闲超时（秒），超时自动断开

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
