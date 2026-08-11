# -*- coding: utf-8 -*-

DEFAULT_CONFIG = {
    "black_list": [],
    "OpenQQ": {
        "appid": "",
        "secret": "",
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
        "ai_price_input": 1.0,
        "ai_price_output": 2.0,
    },
    "Log_level": "INFO",
    "webadmin": {
        "enabled": True,
        "host": "0.0.0.0",
        "port": 8765,
        "password": "",
    },
    "scheduled_send": {
        "send_time": "06:00",
        "default_content": "早生蚝",
        "notify_groups": [],
        "admin_user": "",
        "enabled": True,
    },
}

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
    "STAR_AI_PRICE_INPUT": ("Others", "ai_price_input"),
    "STAR_AI_PRICE_OUTPUT": ("Others", "ai_price_output"),
    "STAR_BOT_NAME": ("Others", "bot_name"),
    "STAR_BOT_NAME_EN": ("Others", "bot_name_en"),
    "STAR_BOT_REMINDER": ("Others", "reminder"),
    "STAR_BOT_ROOT_USER": ("Others", "ROOT_User"),
    "STAR_BOT_DEFAULT_MODE": ("Others", "default_mode"),
    "STAR_BOT_ALLOW_AI": ("Others", "allow_ai"),
    "STAR_LOG_LEVEL": "Log_level",
    "STAR_BLACK_LIST": "black_list",
    "STAR_TRAVELLER_ADMIN_ENABLED": ("webadmin", "enabled"),
    "STAR_TRAVELLER_ADMIN_HOST": ("webadmin", "host"),
    "STAR_TRAVELLER_ADMIN_PORT": ("webadmin", "port"),
    "STAR_TRAVELLER_ADMIN_PASSWORD": ("webadmin", "password"),
    "STAR_SCHEDULED_SEND_TIME": ("scheduled_send", "send_time"),
    "STAR_SCHEDULED_SEND_CONTENT": ("scheduled_send", "default_content"),
    "STAR_SCHEDULED_SEND_GROUPS": ("scheduled_send", "notify_groups"),
    "STAR_SCHEDULED_SEND_ADMIN": ("scheduled_send", "admin_user"),
    "STAR_SCHEDULED_SEND_ENABLED": ("scheduled_send", "enabled"),
}

_INT_KEYS = {"STAR_AI_MAX_TOKENS", "STAR_TRAVELLER_ADMIN_PORT"}
_FLOAT_KEYS = {"STAR_AI_TEMPERATURE", "STAR_AI_PRICE_INPUT", "STAR_AI_PRICE_OUTPUT"}
_BOOL_KEYS = {"STAR_BOT_ALLOW_AI", "STAR_TRAVELLER_ADMIN_ENABLED", "STAR_SCHEDULED_SEND_ENABLED"}
_LIST_KEYS = {"STAR_BOT_ROOT_USER", "STAR_BLACK_LIST", "STAR_SCHEDULED_SEND_GROUPS"}
