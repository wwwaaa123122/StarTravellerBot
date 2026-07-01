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
from pathlib import Path

# 获取项目根目录 (open-qq 的父目录)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPENQQ_DIR = os.path.dirname(os.path.abspath(__file__))

# 设置工作目录为项目根目录
os.chdir(PROJECT_ROOT)

# 将项目根目录和 open-qq 目录添加到 path
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, OPENQQ_DIR)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# 抑制 pynvml 弃用警告
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# 只在导入原项目模块时临时抑制输出
import io
_old_stdout = sys.stdout
sys.stdout = io.StringIO()

from client import XCLRClient

sys.stdout = _old_stdout

import logging as std_logging


def load_config() -> dict:
    """加载配置文件"""
    config_path = os.path.join(PROJECT_ROOT, "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    """主入口函数"""
    # 加载主配置
    config = load_config()
    
    # 从 config.json 读取 QQ 开放平台凭证
    openqq = config.get("OpenQQ", {})
    appid = openqq.get("appid")
    secret = openqq.get("secret")
    
    if not appid or not secret:
        print("错误: 请在 config.json 中配置 OpenQQ.appid 和 OpenQQ.secret")
        sys.exit(1)
    
    # 设置日志级别
    log_level = config.get("Log_level", "INFO")
    log_level_map = {
        "DEBUG": std_logging.DEBUG,
        "INFO": std_logging.INFO,
        "WARNING": std_logging.WARNING,
        "ERROR": std_logging.ERROR,
        "CRITICAL": std_logging.CRITICAL,
    }
    log_level_value = log_level_map.get(log_level.upper(), std_logging.INFO)
    
    # 启动信息
    bot_name = config.get("Others", {}).get("bot_name", "星辰旅人")
    version = "3.1 - Next Release"
    
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║                    {bot_name} - QQ 开放平台机器人                ║
║                         Version: {version}                       ║
╚══════════════════════════════════════════════════════════════════╝
""")
    
    # 创建客户端
    client = XCLRClient(
        config=config,
        log_level=log_level_value,
        is_sandbox=False,  # 沙箱环境
    )
    
    # 运行机器人
    client.run(appid=appid, secret=secret)


if __name__ == "__main__":
    main()
