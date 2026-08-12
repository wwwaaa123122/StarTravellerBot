# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from dataclasses import fields as _fields


def _pick(cls, source: dict) -> dict:
    names = {f.name for f in _fields(cls)}
    return {k: v for k, v in source.items() if k in names}


@dataclass
class QQSettings:
    appid: str = ""
    secret: str = ""


@dataclass
class AISettings:
    deepseek_key: str = ""
    gemini_key: str = ""
    openai_key: str = ""
    ai_base_url: str = "https://api.deepseek.com"
    ai_model: str = "deepseek-v4-flash"
    ai_max_tokens: int = 2000
    ai_temperature: float = 0.7
    ai_price_input: float = 1.0
    ai_price_output: float = 2.0


@dataclass
class BotSettings:
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

    def __init__(self, data: dict):
        self.data = data
        self.qq = QQSettings(**_pick(QQSettings, data.get("OpenQQ", {})))
        self.ai = AISettings(**_pick(AISettings, data.get("Others", {})))
        self.bot = BotSettings(**_pick(BotSettings, data.get("Others", {})))
        self.webadmin = WebAdminSettings(**_pick(WebAdminSettings, data.get("webadmin", {})))
        self.log_level = str(data.get("Log_level", "INFO")).upper()

    def to_dict(self) -> dict:
        return self.data
