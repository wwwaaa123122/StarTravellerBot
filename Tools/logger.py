# -*- coding: utf-8 -*-
"""统一日志系统 —— 基于 loguru，拦截标准库 logging 统一输出。

使用方式：
    from Tools.logger import setup_logging
    setup_logging("INFO")  # 在 main.py 启动时调用一次即可

之后所有 logging.getLogger(...) 和 loguru logger 都会统一输出到控制台和日志文件。
"""

import logging
import os
import sys

from loguru import logger

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(PROJECT_ROOT, "data", "logs")

# 拦截配置状态
_intercept_installed = False


class _InterceptHandler(logging.Handler):
    """将标准库 logging 日志路由到 loguru。"""

    def emit(self, record: logging.LogRecord):
        # 跳过 loguru 自身的日志避免死循环
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging(level: str = "INFO") -> None:
    """配置 loguru 全局日志系统。

    - 控制台彩色输出 (stderr)
    - 按天轮转的文件日志 (data/logs/)
    - 拦截标准库 logging，统一路由到 loguru
    """
    global _intercept_installed

    # 移除默认 handler
    logger.remove()

    # 控制台输出（彩色）
    logger.add(
        sys.stderr,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        level=level.upper(),
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # 文件日志（按天轮转，保留 7 天）
    os.makedirs(LOG_DIR, exist_ok=True)
    logger.add(
        os.path.join(LOG_DIR, "bot_{time:YYYY-MM-DD}.log"),
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="00:00",
        retention="7 days",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    # 拦截标准库 logging
    if not _intercept_installed:
        logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
        _intercept_installed = True

    # 静默第三方库的 noisy logger
    for lib in ("httpx", "httpcore", "urllib3", "asyncio", "websockets"):
        logging.getLogger(lib).setLevel(logging.WARNING)

    logger.info(f"日志系统已初始化 (level={level.upper()})")