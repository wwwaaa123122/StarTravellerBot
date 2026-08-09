# -*- coding: utf-8 -*-
"""类型化配置访问：对合并后的配置 dict 提供属性式读取。"""

from dataclasses import dataclass, field, fields as _fields


def _pick(cls, source: dict) -> dict:
    names = {f.name for f in _fields(cls)}
    return {k: v for k, v in source.items() if k in names}


@dataclass
class QQSettings:
    """字段名与 config.json OpenQQ 段保持一致。"""
    appid: str = ""
    secret: str = ""
    sandbox: bool = True


@dataclass
class AISettings:
    """字段名与 config.json Others 段保持一致。"""
    deepseek_key: str = ""
    gemini_key: str = ""
    openai_key: str = ""
    ai_base_url: str = "https://api.deepseek.com"
    ai_model: str = "deepseek-v4-flash"
    ai_max_tokens: int = 2000
    ai_temperature: float = 0.7
    ai_rate_limit_user: int = 10
    ai_rate_limit_global: int = 60
    ai_price_input: float = 1.0
    ai_price_output: float = 2.0


@dataclass
class BotSettings:
    """字段名与 config.json Others 段保持一致。"""
    bot_name: str = "星辰旅人"
    bot_name_en: str = "XCLR"
    reminder: str = "#"
    ROOT_User: list = field(default_factory=list)
    default_mode: str = "Ds"
    allow_ai: bool = True


@dataclass
class WebAdminSettings:
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8765
    password: str = ""


class Settings:
    """包装配置 dict，提供类型化访问；data 为与旧版兼容的原始 dict。"""

    def __init__(self, data: dict):
        self.data = data
        self.qq = QQSettings(**_pick(QQSettings, data.get("OpenQQ", {})))
        self.ai = AISettings(**_pick(AISettings, data.get("Others", {})))
        self.bot = BotSettings(**_pick(BotSettings, data.get("Others", {})))
        self.webadmin = WebAdminSettings(**_pick(WebAdminSettings, data.get("webadmin", {})))
        self.log_level = str(data.get("Log_level", "INFO")).upper()

    def to_dict(self) -> dict:
        return self.data
