# -*- coding: utf-8 -*-
"""配置加载：.env -> config.json -> 环境变量覆盖 -> 默认值兜底。

优先级：环境变量 > .env > config.json > 默认值。
返回与旧版一致的 dict 结构（OpenQQ/Others/Log_level/webadmin），兼容现有消费者。
"""

import json
import os

from config.defaults import DEFAULT_CONFIG, ENV_MAP, _INT_KEYS, _FLOAT_KEYS

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.json")


def load_env_file(env_path: str = ENV_PATH) -> None:
    """加载 .env 到 os.environ（不覆盖已有环境变量）。"""
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


def _coerce(env_key: str, value: str):
    if env_key in _INT_KEYS:
        try:
            return int(value)
        except ValueError:
            return value
    if env_key in _FLOAT_KEYS:
        try:
            return float(value)
        except ValueError:
            return value
    return value


def _apply_env(data: dict) -> dict:
    """将环境变量中的敏感值注入配置（优先级高于 config.json）。"""
    for env_key, (section, cfg_key) in ENV_MAP.items():
        val = os.environ.get(env_key)
        if val is not None and val != "":
            data.setdefault(section, {})[cfg_key] = _coerce(env_key, val)
    return data


def _merge_deep(base: dict, override: dict) -> dict:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge_deep(base[key], value)
        else:
            base[key] = value
    return base


def load_config(config_path: str = CONFIG_PATH) -> dict:
    """加载合并后的完整配置 dict。"""
    data = json.loads(json.dumps(DEFAULT_CONFIG))
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            file_cfg = json.load(f)
        _merge_deep(data, file_cfg)
    return _apply_env(data)


def load_settings(config_path: str = CONFIG_PATH):
    """加载配置并返回 Settings 类型化访问对象。"""
    from config.schema import Settings
    return Settings(load_config(config_path))
