"""loguru 日志配置：控制台 + 文件滚动（UTF-8，Windows 中文安全）。"""
import sys
from pathlib import Path

from loguru import logger

_configured = False


def configure_logs() -> None:
    """幂等初始化：控制台彩色 + logs/app.log 滚动（10MB × 5 份）。"""
    global _configured
    if _configured:
        return
    _configured = True
    Path("logs").mkdir(exist_ok=True)
    logger.remove()  # 移除默认 stderr handler
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:MM-DD HH:mm:ss}</green> | <level>{level: <7}</level> | <cyan>{name}</cyan> - {message}",
    )
    logger.add(
        "logs/app.log",
        level="INFO",
        encoding="utf-8",  # Windows 关键：默认 gbk 会炸中文
        rotation="10 MB",
        retention=5,
        enqueue=True,  # 多线程安全写
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <7} | {name}:{function}:{line} - {message}",
    )
