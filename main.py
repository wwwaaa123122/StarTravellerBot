# -*- coding: utf-8 -*-
"""
星辰旅人 QQ 开放平台机器人
基于 qqbot_openapi（QQ 开放平台轻量 SDK，本项目内 pip 包）

文档: https://bot.q.qq.com/wiki/develop/pythonsdk/
"""

import os
import sys

from loguru import logger

# 当前仓库即项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 设置工作目录为项目根目录
os.chdir(PROJECT_ROOT)

# 将项目根目录添加到 path
sys.path.insert(0, PROJECT_ROOT)

# 抑制 pynvml 弃用警告
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# 只在导入原项目模块时临时抑制输出
import io
_old_stdout = sys.stdout
sys.stdout = io.StringIO()

from client import XCLRClient

sys.stdout = _old_stdout


def main():
    """主入口函数"""
    from config import load_settings

    # 加载 .env + config.json，环境变量优先
    settings = load_settings()

    # 初始化日志系统
    from Tools.logger import setup_logging
    setup_logging(settings.log_level)

    appid = settings.qq.appid
    secret = settings.qq.secret

    if not appid or not secret:
        logger.error("请设置 STAR_QO_APPID / STAR_QO_SECRET 环境变量，或在 config.json 中配置 OpenQQ")
        sys.exit(1)

    # 启动信息
    from Tools.core import VERSION_NAME
    logger.info(f"{settings.bot.bot_name} - QQ 开放平台机器人 v{VERSION_NAME} 正在启动")

    # 创建客户端
    import logging as _logging
    client = XCLRClient(
        config=settings.to_dict(),
        log_level=getattr(_logging, settings.log_level, 20),
        is_sandbox=settings.qq.sandbox,
    )

    # 按配置同步启动管理后台（守护线程）
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

    # 运行机器人
    client.run(appid=appid, secret=secret)


if __name__ == "__main__":
    main()
