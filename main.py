# -*- coding: utf-8 -*-

import os
import sys

from loguru import logger

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

os.chdir(PROJECT_ROOT)

sys.path.insert(0, PROJECT_ROOT)

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import io
_old_stdout = sys.stdout
sys.stdout = io.StringIO()

from client import XCLRClient

sys.stdout = _old_stdout


def main():
    from config import load_settings

    settings = load_settings()

    from Tools.logger import setup_logging
    setup_logging(settings.log_level)

    appid = settings.qq.appid
    secret = settings.qq.secret

    if not appid or not secret:
        logger.error("请设置 STAR_QO_APPID / STAR_QO_SECRET 环境变量（或写入 .env 文件）")
        sys.exit(1)

    from Tools.core import VERSION_NAME
    logger.info(f"{settings.bot.bot_name} - QQ 开放平台机器人 v{VERSION_NAME} 正在启动")

    import logging as _logging
    client = XCLRClient(
        config=settings.to_dict(),
        log_level=getattr(_logging, settings.log_level, 20),
        is_sandbox=settings.qq.sandbox,
    )

    if settings.webadmin.enabled:
        try:
            from webadmin.server import start_server
            start_server(
                host=settings.webadmin.host,
                port=settings.webadmin.port,
                password=settings.webadmin.password,
            )
        except Exception as exc:
            logger.error(f"管理后台启动失败: {exc}")
    else:
        logger.info("管理后台已在配置中禁用，跳过启动")

    client.run(appid=appid, secret=secret)


if __name__ == "__main__":
    main()
