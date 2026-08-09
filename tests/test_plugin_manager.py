# -*- coding: utf-8 -*-
"""PluginManager 测试：插件加载 / TRIGGER 拼写兼容 / Any 排序 / skip_plugins。"""

import logging
import types

import pytest

from core.plugin_manager import PluginManager

_PLUGIN_TEMPLATE = """\
TRIGGER_KEYWORD = "{kw}"
HELP_MESSAGE = "{help}"

async def on_message(event, actions, **kwargs):
    return True
"""

_ANY_PLUGIN = """\
TRIGGER_KEYWORDS = ["Any"]
HELP_MESSAGE = "any-help"

async def on_message(event, actions, **kwargs):
    return True
"""

# 旧拼写插件：验证向后兼容
_LEGACY_PLUGIN = """\
TRIGGHT_KEYWORD = "旧版"
HELP_MESSAGE = "legacy-help"

async def on_message(event, actions, **kwargs):
    return True
"""


def _make_client():
    client = types.SimpleNamespace()
    client.logger = logging.getLogger("test-plugin-manager")
    client.reminder = "#"
    client.bot_name = "测试"
    client.root_users = []
    client.config = {}
    client._try_get_nickname = lambda message: ""
    return client


def _write_plugin(tmp_path, name: str, content: str):
    (tmp_path / name).write_text(content, encoding="utf-8")


@pytest.fixture
def manager():
    return PluginManager(_make_client())


def test_load_plugins_with_trigger(tmp_path, manager):
    _write_plugin(tmp_path, "ping.py", _PLUGIN_TEMPLATE.format(kw="ping ", help="ping 测试"))
    _write_plugin(tmp_path, "hitokoto.py", _PLUGIN_TEMPLATE.format(kw="一言", help="一言"))
    _write_plugin(tmp_path, "any.py", _ANY_PLUGIN)
    manager.load_plugins(plugin_dir=str(tmp_path))
    names = [p["name"] for p in manager.plugins]
    assert sorted(names) == ["any", "hitokoto", "ping"]
    # Any 插件排在最后
    assert manager.plugins[-1]["name"] == "any"


def test_load_plugins_skips_disabled_and_dunder(tmp_path, manager):
    _write_plugin(tmp_path, "ping.py", _PLUGIN_TEMPLATE.format(kw="ping", help="ping"))
    _write_plugin(tmp_path, "__init__.py", "")
    _write_plugin(tmp_path, "d_disabled.py", _PLUGIN_TEMPLATE.format(kw="x", help="x"))
    _write_plugin(tmp_path, "notes.txt", "not a plugin")
    manager.load_plugins(plugin_dir=str(tmp_path))
    assert [p["name"] for p in manager.plugins] == ["ping"]


def test_legacy_trigg_ht_keyword_compat(tmp_path, manager):
    _write_plugin(tmp_path, "legacy.py", _LEGACY_PLUGIN)
    manager.load_plugins(plugin_dir=str(tmp_path))
    assert len(manager.plugins) == 1
    assert manager.plugins[0]["keywords"] == ["旧版"]


def test_plugin_without_keyword_skipped(tmp_path, manager):
    (tmp_path / "nokey.py").write_text(
        "HELP_MESSAGE = 'x'\n\nasync def on_message(event, actions, **kwargs):\n    return True\n",
        encoding="utf-8",
    )
    manager.load_plugins(plugin_dir=str(tmp_path))
    assert manager.plugins == []


def test_try_plugins_match_and_skip(tmp_path, manager):
    _write_plugin(tmp_path, "ping.py", _PLUGIN_TEMPLATE.format(kw="ping", help="ping"))
    manager.load_plugins(plugin_dir=str(tmp_path))

    msg = types.SimpleNamespace(author=types.SimpleNamespace(member_openid="u1", user_openid="u1"))
    result = __import__("asyncio").get_event_loop_policy().new_event_loop()
    try:
        assert result.run_until_complete(manager.try_plugins(msg, "ping 测试")) is True
        assert result.run_until_complete(manager.try_plugins(msg, "ping", skip_plugins={"ping"})) is False
        assert result.run_until_complete(manager.try_plugins(msg, "无关内容")) is False
    finally:
        result.close()


def test_get_help_text_includes_plugins(tmp_path, manager):
    _write_plugin(tmp_path, "weather.py", _PLUGIN_TEMPLATE.format(kw="天气", help="天气 查询"))
    manager.load_plugins(plugin_dir=str(tmp_path))
    text = manager.get_help_text("星辰旅人", "1.0")
    assert "星辰旅人" in text
    assert "天气 查询" in text
