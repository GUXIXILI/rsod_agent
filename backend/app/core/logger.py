"""
统一日志配置模块
提供日志初始化（setup_logging）和便捷获取（get_logger）功能
控制台输出 DEBUG 级别，文件输出 INFO 级别（支持轮转）
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from app.config.settings import settings


def setup_logging() -> None:
    """
    配置根日志器，统一管理所有日志输出：

    1. 控制台 Handler（StreamHandler）：
       - 输出 DEBUG 及以上级别
       - 格式：时间 | 级别 | 模块:函数:行号 | 消息

    2. 文件 Handler（RotatingFileHandler）：
       - 输出 INFO 及以上级别
       - 写入 settings.LOG_DIR / app.log
       - 单文件最大 settings.LOG_MAX_BYTES（默认 10MB）
       - 保留 settings.LOG_BACKUP_COUNT（默认 5）份备份

    3. stderr Handler（StreamHandler）：
       - 输出 ERROR 及以上级别到 stderr
       - 供 startup_backend_err.log 监控 ERR 日志

    4. 降低第三方库日志噪音：
       - uvicorn / sqlalchemy / minio / httpx → WARNING 级别
    """
    # ── 确保日志目录存在 ──────────────────────────────
    log_dir = settings.LOG_DIR
    os.makedirs(log_dir, exist_ok=True)

    # ── 获取根日志器 ──────────────────────────────────
    root_logger = logging.getLogger()
    # 避免重复添加 Handler（幂等性保护）
    if root_logger.handlers:
        return
    root_logger.setLevel(logging.DEBUG)

    # ── 统一日志格式 ──────────────────────────────────
    # 格式：时间 | 级别(8字符左对齐) | logger名:函数名:行号 | 消息
    log_format = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── 1. 控制台 Handler ─────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)

    # ── 2. 文件 Handler（RotatingFileHandler）─────────
    log_file_path = os.path.join(log_dir, "app.log")
    file_handler = RotatingFileHandler(
        filename=log_file_path,
        maxBytes=settings.LOG_MAX_BYTES,          # 单文件最大字节数
        backupCount=settings.LOG_BACKUP_COUNT,    # 保留备份数量
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)

    # ── 3. stderr Handler（ERROR 级别日志输出到 stderr，供 startup_backend_err.log 监控）──
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.ERROR)  # 只输出 ERROR 及以上级别
    stderr_handler.setFormatter(log_format)
    root_logger.addHandler(stderr_handler)

    # ── 4. 降低第三方库日志噪音 ──────────────────────
    for lib_name in ("uvicorn", "sqlalchemy", "minio", "httpx"):
        logging.getLogger(lib_name).setLevel(logging.WARNING)

    # SQLAlchemy 的 SQL 语句由 sqlalchemy.engine.Engine 子 logger 输出，
    # session.py 中 echo=settings.DEBUG 会触发该 logger 输出 INFO 级别的 SQL。
    # 1) 将其级别设为 WARNING，阻止 INFO 级 SQL 进入日志；
    # 2) 关闭 propagate，防止 Engine 自带的 StreamHandler 将 SQL 传播到根 logger 的文件 Handler。
    engine_logger = logging.getLogger("sqlalchemy.engine.Engine")
    engine_logger.setLevel(logging.WARNING)
    engine_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """
    便捷方法：返回指定名称的 logger

    参数：
        name: logger 名称，通常使用 __name__

    返回：
        logging.Logger 实例
    """
    return logging.getLogger(name)