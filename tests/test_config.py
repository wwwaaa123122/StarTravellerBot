# -*- coding: utf-8 -*-

import os

import pytest

from config import load_config, load_settings
from config.loader import load_env_file


@pytest.fixture
def _clean_env(monkeypatch):
    for key in list(os.environ):
        if key.startswith("STAR_"):
            monkeypatch.delenv(key, raising=False)


def _write_env(tmp_path, text):
    path = tmp_path / ".env"
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_defaults_without_file(tmp_path, _clean_env):
    cfg = load_config(str(tmp_path / "missing.env"))
    assert cfg["Others"]["bot_name"] == "星辰旅人"
    assert cfg["Others"]["ai_model"] == "deepseek-v4-flash"
    assert cfg["OpenQQ"]["sandbox"] is True
    assert cfg["webadmin"]["port"] == 8765


def test_load_from_env_file(tmp_path, _clean_env):
    path = _write_env(tmp_path, (
        "STAR_QO_APPID=123\n"
        "STAR_QO_SANDBOX=false\n"
        "STAR_BOT_NAME=测试机器人\n"
        "STAR_BOT_ROOT_USER=u1,u2\n"
        "STAR_BLACK_LIST=evil1, evil2\n"
        "STAR_LOG_LEVEL=DEBUG\n"
    ))
    cfg = load_config(path)
    assert cfg["OpenQQ"]["appid"] == "123"
    assert cfg["OpenQQ"]["sandbox"] is False
    assert cfg["Others"]["bot_name"] == "测试机器人"
    assert cfg["Others"]["ROOT_User"] == ["u1", "u2"]
    assert cfg["black_list"] == ["evil1", "evil2"]
    assert cfg["Log_level"] == "DEBUG"
    assert cfg["Others"]["ai_max_tokens"] == 2000


def test_env_overrides_env_file(tmp_path, _clean_env, monkeypatch):
    path = _write_env(tmp_path, "STAR_AI_MODEL=gpt-4o\nSTAR_AI_MAX_TOKENS=1000\n")
    monkeypatch.setenv("STAR_AI_MODEL", "deepseek-chat")
    monkeypatch.setenv("STAR_AI_MAX_TOKENS", "4096")
    monkeypatch.setenv("STAR_AI_TEMPERATURE", "1.1")
    monkeypatch.setenv("STAR_TRAVELLER_ADMIN_PORT", "9999")
    cfg = load_config(path)
    assert cfg["Others"]["ai_model"] == "deepseek-chat"
    assert cfg["Others"]["ai_max_tokens"] == 4096
    assert cfg["Others"]["ai_temperature"] == 1.1
    assert cfg["webadmin"]["port"] == 9999


def test_coerce_types(tmp_path, _clean_env):
    path = _write_env(tmp_path, (
        "STAR_BOT_ALLOW_AI=false\n"
        "STAR_AI_PRICE_INPUT=0.5\n"
        "STAR_SCHEDULED_SEND_GROUPS=g1,g2\n"
        "STAR_TRAVELLER_ADMIN_ENABLED=0\n"
    ))
    cfg = load_config(path)
    assert cfg["Others"]["allow_ai"] is False
    assert cfg["Others"]["ai_price_input"] == 0.5
    assert cfg["scheduled_send"]["notify_groups"] == ["g1", "g2"]
    assert cfg["webadmin"]["enabled"] is False


def test_load_env_file(tmp_path, _clean_env, monkeypatch):
    env = tmp_path / ".env"
    env.write_text(
        "# 注释\nSTAR_QO_APPID=from_env\nSTAR_QO_SECRET=\"quoted\"\nEMPTY=\n",
        encoding="utf-8",
    )
    load_env_file(str(env))
    assert os.environ["STAR_QO_APPID"] == "from_env"
    assert os.environ["STAR_QO_SECRET"] == "quoted"
    assert os.environ["EMPTY"] == ""


def test_settings_typed_access(tmp_path, _clean_env):
    path = _write_env(tmp_path, (
        "STAR_QO_APPID=a1\n"
        "STAR_QO_SECRET=s1\n"
        "STAR_BOT_NAME=小星\n"
        "STAR_BOT_ROOT_USER=u1\n"
        "STAR_BOT_ALLOW_AI=false\n"
    ))
    s = load_settings(path)
    assert s.qq.appid == "a1"
    assert s.qq.secret == "s1"
    assert s.bot.bot_name == "小星"
    assert s.bot.ROOT_User == ["u1"]
    assert s.bot.allow_ai is False
    assert s.log_level == "INFO"
    assert s.webadmin.port == 8765


def test_webadmin_write_env(tmp_path, _clean_env, monkeypatch):
    import webadmin.server as ws
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# 注释\nSTAR_QO_APPID=keep\nSTAR_BOT_NAME=旧名\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ws, "ENV_FILE", str(env_file))
    ws._write_env({"STAR_BOT_NAME": "新名", "STAR_LOG_LEVEL": "DEBUG"})
    text = env_file.read_text(encoding="utf-8")
    assert "# 注释" in text
    assert "STAR_QO_APPID=keep" in text
    assert "STAR_BOT_NAME=新名" in text
    assert "STAR_LOG_LEVEL=DEBUG" in text
    cfg = load_config(str(env_file))
    assert cfg["Others"]["bot_name"] == "新名"
    assert cfg["Log_level"] == "DEBUG"
