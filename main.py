# -*- coding: utf-8 -*-
"""
星辰旅人 QQ 开放平台机器人
基于 botpy (QQ Official Bot Python SDK)

文档: https://bot.q.qq.com/wiki/develop/pythonsdk/
"""

import os
import sys
import json
import logging
import warnings

OPENQQ_DIR = os.path.dirname(os.path.abspath(__file__))

# 添加 open-qq 目录到 path
sys.path.insert(0, OPENQQ_DIR)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
warnings.filterwarnings("ignore", category=FutureWarning)

from client import XCLRClient


def load_config() -> dict:
    """加载配置文件"""
    # 优先加载 open-qq 本地 config.json，不存在则加载父项目的
    local = os.path.join(OPENQQ_DIR, "config.json")
    parent = os.path.join(os.path.dirname(OPENQQ_DIR), "config.json")
    path = local if os.path.exists(local) else parent
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    config = load_config()

    openqq = config.get("OpenQQ", {})
    appid = openqq.get("appid")
    secret = openqq.get("secret")

    if not appid or not secret:
        print("错误: 请在 config.json 中配置 OpenQQ.appid 和 OpenQQ.secret")
        sys.exit(1)

    log_level = config.get("Log_level", "INFO")
    log_level_map = {
        "DEBUG": logging.DEBUG, "INFO": logging.INFO,
        "WARNING": logging.WARNING, "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    bot_name = config.get("Others", {}).get("bot_name", "星辰旅人")
    version = "3.1 - Next Release"

    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║                    {bot_name} - QQ 开放平台机器人                ║
║                         Version: {version}                       ║
╚══════════════════════════════════════════════════════════════════╝
""")

    client = XCLRClient(
        config=config,
        log_level=log_level_map.get(log_level.upper(), logging.INFO),
        is_sandbox=False,
    )
    client.run(appid=appid, secret=secret)


if __name__ == "__main__":
    main()
