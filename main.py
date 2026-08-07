# -*- coding: utf-8 -*-
"""
星辰旅人 QQ 开放平台机器人
基于 qqbot_openapi（QQ 开放平台轻量 SDK，本项目内 pip 包）

文档: https://bot.q.qq.com/wiki/develop/pythonsdk/
"""

import os
import sys
import json

from loguru import logger

# 当前仓库即项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 设置工作目录为项目根目录
os.chdir(PROJECT_ROOT)

# 将项目根目录添加到 path
sys.path.insert(0, PROJECT_ROOT)


def _load_env_file():
    """加载项目根目录下的 .env 文件到 os.environ（不覆盖已有环境变量）。"""
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def _inject_env_secrets(config: dict) -> dict:
    """将环境变量中的敏感值注入 config 字典（优先级高于 config.json）。"""
    others = config.setdefault("Others", {})

    env_map = {
        "STAR_DEEPSEEK_KEY": ("Others", "deepseek_key"),
        "STAR_GEMINI_KEY": ("Others", "gemini_key"),
        "STAR_OPENAI_KEY": ("Others", "openai_key"),
        "STAR_AI_BASE_URL": ("Others", "ai_base_url"),
        "STAR_AI_MODEL": ("Others", "ai_model"),
        "STAR_AI_MAX_TOKENS": ("Others", "ai_max_tokens"),
        "STAR_AI_TEMPERATURE": ("Others", "ai_temperature"),
    }

    for env_key, (section, cfg_key) in env_map.items():
        val = os.environ.get(env_key)
        if val:
            if section == "Others":
                try:
                    others[cfg_key] = int(val)
                except ValueError:
                    try:
                        others[cfg_key] = float(val)
                    except ValueError:
                        others[cfg_key] = val

    return config

# 抑制 pynvml 弃用警告
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# 只在导入原项目模块时临时抑制输出
import io
_old_stdout = sys.stdout
sys.stdout = io.StringIO()

from client import XCLRClient

sys.stdout = _old_stdout


def load_config() -> dict:
    """加载项目根目录下的 config.json 配置文件"""
    config_path = os.path.join(PROJECT_ROOT, "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    """主入口函数"""
    # 加载 .env 环境变量
    _load_env_file()

    # 加载主配置
    config = load_config()

    # 注入环境变量中的敏感值
    config = _inject_env_secrets(config)

    # 初始化日志系统
    from Tools.logger import setup_logging
    log_level = config.get("Log_level", "INFO")
    setup_logging(log_level)

    # 从环境变量或 config.json 读取 QQ 开放平台凭证
    appid = os.environ.get("STAR_QO_APPID") or config.get("OpenQQ", {}).get("appid")
    secret = os.environ.get("STAR_QO_SECRET") or config.get("OpenQQ", {}).get("secret")

    if not appid or not secret:
        logger.error("请设置 STAR_QO_APPID / STAR_QO_SECRET 环境变量，或在 config.json 中配置 OpenQQ")
        sys.exit(1)

    # 启动信息
    bot_name = config.get("Others", {}).get("bot_name", "星辰旅人")
    from Tools.core import VERSION_NAME
    version = VERSION_NAME
    logger.info(f"{bot_name} - QQ 开放平台机器人 v{version} 正在启动")
    
    # 创建客户端
    is_sandbox = config.get("OpenQQ", {}).get("sandbox", False)
    client = XCLRClient(
        config=config,
        log_level=getattr(__import__("logging"), log_level.upper(), 20),
        is_sandbox=is_sandbox,
    )

    # 按 config.json 的 webadmin 段同步启动管理后台（守护线程）
    webadmin_cfg = config.get("webadmin", {}) or {}
    if webadmin_cfg.get("enabled", True):
        try:
            from webadmin.server import start_server
            start_server(
                host=webadmin_cfg.get("host"),
                port=webadmin_cfg.get("port"),
                password=os.environ.get("STAR_TRAVELLER_ADMIN_PASSWORD") or webadmin_cfg.get("password"),
            )
        except Exception as exc:
            logger.error(f"管理后台启动失败: {exc}")
    else:
        logger.info("管理后台已在 config.json 中禁用，跳过启动")

    # 运行机器人
    client.run(appid=appid, secret=secret)


if __name__ == "__main__":
    main()
