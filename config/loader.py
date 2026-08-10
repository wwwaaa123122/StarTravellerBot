# -*- coding: utf-8 -*-

import copy
import os

from config.defaults import DEFAULT_CONFIG, ENV_MAP, _INT_KEYS, _FLOAT_KEYS, _BOOL_KEYS, _LIST_KEYS

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")


def load_env_file(env_path: str = ENV_PATH) -> None:
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
    if env_key in _BOOL_KEYS:
        return value.strip().lower() in ("1", "true", "yes", "on")
    if env_key in _LIST_KEYS:
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


def _apply_env(data: dict) -> dict:
    for env_key, target in ENV_MAP.items():
        val = os.environ.get(env_key)
        if val is None or val == "":
            continue
        if isinstance(target, str):
            data[target] = _coerce(env_key, val)
        else:
            section, cfg_key = target
            data.setdefault(section, {})[cfg_key] = _coerce(env_key, val)
    return data


def load_config(env_path: str = ENV_PATH) -> dict:
    load_env_file(env_path)
    data = copy.deepcopy(DEFAULT_CONFIG)
    return _apply_env(data)


def load_settings(env_path: str = ENV_PATH):
    from config.schema import Settings
    return Settings(load_config(env_path))
