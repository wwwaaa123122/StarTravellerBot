# -*- coding: utf-8 -*-
"""配置加载测试：默认值 / config.json 合并 / 环境变量覆盖。"""

import json
import os

import pytest

from config import load_config, load_settings


@pytest.fixture
def _clean_env(monkeypatch):
    for key in ("STAR_QO_APPID", "STAR_QO_SECRET", "STAR_AI_MAX_TOKENS",
                "STAR_AI_TEMPERATURE", "STAR_TRAVELLER_ADMIN_PORT"):
        monkeypatch.delenv(key, raising=False)


def _write_config(tmp_path, data):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(path)


def test_defaults_without_file(tmp_path, _clean_env):
    cfg = load_config(str(tmp_path / "missing.json"))
    assert cfg["Others"]["bot_name"] == "星辰旅人"
    assert cfg["Others"]["ai_model"] == "deepseek-v4-flash"
    assert cfg["OpenQQ"]["sandbox"] is True
    assert cfg["webadmin"]["port"] == 8765


def test_merge_with_config_file(tmp_path, _clean_env):
    path = _write_config(tmp_path, {
        "OpenQQ": {"appid": "123", "sandbox": False},
        "Others": {"bot_name": "测试机器人", "ai_model": "gpt-4o"},
    })
    cfg = load_config(path)
    assert cfg["OpenQQ"]["appid"] == "123"
    assert cfg["OpenQQ"]["sandbox"] is False
    assert cfg["Others"]["bot_name"] == "测试机器人"
    assert cfg["Others"]["ai_model"] == "gpt-4o"
    # 未配置字段保留默认值
    assert cfg["Others"]["ai_max_tokens"] == 2000


def test_env_overrides_config(tmp_path, _clean_env, monkeypatch):
    path = _write_config(tmp_path, {"Others": {"ai_model": "gpt-4o"}})
    monkeypatch.setenv("STAR_AI_MODEL", "deepseek-chat")
    monkeypatch.setenv("STAR_AI_MAX_TOKENS", "4096")
    monkeypatch.setenv("STAR_AI_TEMPERATURE", "1.1")
    monkeypatch.setenv("STAR_TRAVELLER_ADMIN_PORT", "9999")
    cfg = load_config(path)
    assert cfg["Others"]["ai_model"] == "deepseek-chat"
    assert cfg["Others"]["ai_max_tokens"] == 4096
    assert cfg["Others"]["ai_temperature"] == 1.1
    assert cfg["webadmin"]["port"] == 9999


def test_load_env_file(tmp_path, _clean_env, monkeypatch):
    env = tmp_path / ".env"
    env.write_text(
        "# 注释\nSTAR_QO_APPID=from_env\nSTAR_QO_SECRET=\"quoted\"\nEMPTY=\n",
        encoding="utf-8",
    )
    from config.loader import load_env_file
    load_env_file(str(env))
    assert os.environ["STAR_QO_APPID"] == "from_env"
    assert os.environ["STAR_QO_SECRET"] == "quoted"


def test_settings_typed_access(tmp_path, _clean_env):
    path = _write_config(tmp_path, {
        "OpenQQ": {"appid": "a1", "secret": "s1"},
        "Others": {"bot_name": "小星", "ROOT_User": ["u1"], "allow_ai": False},
    })
    s = load_settings(path)
    assert s.qq.appid == "a1"
    assert s.qq.secret == "s1"
    assert s.bot.bot_name == "小星"
    assert s.bot.ROOT_User == ["u1"]
    assert s.bot.allow_ai is False
    assert s.log_level == "INFO"
    assert s.webadmin.port == 8765
