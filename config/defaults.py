# -*- coding: utf-8 -*-
"""配置默认值：config.json 缺省字段的兜底。"""

DEFAULT_CONFIG = {
    "OpenQQ": {
        "appid": "",
        "secret": "",
        "sandbox": True,
    },
    "Others": {
        "bot_name": "星辰旅人",
        "bot_name_en": "XCLR",
        "reminder": "#",
        "ROOT_User": [],
        "default_mode": "Ds",
        "allow_ai": True,
        "deepseek_key": "",
        "gemini_key": "",
        "openai_key": "",
        "ai_base_url": "https://api.deepseek.com",
        "ai_model": "deepseek-v4-flash",
        "ai_max_tokens": 2000,
        "ai_temperature": 0.7,
    },
    "Log_level": "INFO",
    "webadmin": {
        "enabled": True,
        "host": "0.0.0.0",
        "port": 8765,
        "password": "",
    },
}

# 环境变量 -> (配置段, 配置键)
ENV_MAP = {
    "STAR_QO_APPID": ("OpenQQ", "appid"),
    "STAR_QO_SECRET": ("OpenQQ", "secret"),
    "STAR_DEEPSEEK_KEY": ("Others", "deepseek_key"),
    "STAR_GEMINI_KEY": ("Others", "gemini_key"),
    "STAR_OPENAI_KEY": ("Others", "openai_key"),
    "STAR_AI_BASE_URL": ("Others", "ai_base_url"),
    "STAR_AI_MODEL": ("Others", "ai_model"),
    "STAR_AI_MAX_TOKENS": ("Others", "ai_max_tokens"),
    "STAR_AI_TEMPERATURE": ("Others", "ai_temperature"),
    "STAR_TRAVELLER_ADMIN_PASSWORD": ("webadmin", "password"),
    "STAR_TRAVELLER_ADMIN_HOST": ("webadmin", "host"),
    "STAR_TRAVELLER_ADMIN_PORT": ("webadmin", "port"),
}

_INT_KEYS = {"STAR_AI_MAX_TOKENS", "STAR_TRAVELLER_ADMIN_PORT"}
_FLOAT_KEYS = {"STAR_AI_TEMPERATURE"}
_BOOL_KEYS = set()
