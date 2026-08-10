# -*- coding: utf-8 -*-

import logging
import types
from typing import Any

import pytest

from core.dispatcher import Dispatcher, SCENE_C2C, SCENE_GROUP_AT, SCENE_GROUP


class FakeStats:
    def __init__(self):
        self.nicknames = []
        self.messages = 0

    def record_nickname(self, user_id, nickname):
        self.nicknames.append((user_id, nickname))

    def record_message(self):
        self.messages += 1


class FakeClient:
    def __init__(self, plugin_result=False, ai_result=True):
        self.reminder = "#"
        self.bot_name = "测试"
        self.version_name = "1.0"
        self.allow_ai = True
        self.logger = logging.getLogger("test-dispatcher")
        self.config = {}
        self.stats = FakeStats()
        self.context = types.SimpleNamespace(user_lists={})
        self.plugin_hits = []
        self.ai_calls = []
        self.sent = []
        self.ping_hits = 0
        self.plugin_result = plugin_result
        self.ai_result = ai_result
        self.plugin_manager: Any = None

    def _strip_mention(self, content):
        return content.replace("<@!bot1>", "").strip()

    def _try_get_nickname(self, message):
        return ""

    async def _handle_ping(self, message):
        self.ping_hits += 1

    async def _handle_help_command(self, message):
        self.sent.append("help")

    async def _handle_status_command(self, message):
        self.sent.append("status")

    async def _handle_roleplay_command(self, message, content):
        return False

    async def plugin_manager_try(self, message, order, skip_plugins=None):
        self.plugin_hits.append(order)
        return self.plugin_result

    async def _send_message(self, message, content=None, msg_type=0, markdown=None):
        self.sent.append(content or markdown)

    async def _handle_ai_chat(self, message, order, user_id, user_name, use_markdown=False):
        self.ai_calls.append((order, user_id, user_name, use_markdown))

    async def _send_help_image(self, message, help_text):
        self.sent.append(help_text)
        return True


def _make_client(plugin_manager=None, **kw):
    client = FakeClient(**kw)
    if plugin_manager is not None:
        client.plugin_manager = plugin_manager
    else:
        pm = types.SimpleNamespace()
        pm.try_plugins = client.plugin_manager_try
        client.plugin_manager = pm
    return client


def _group_msg(content, group="g1", user="u1"):
    msg = types.SimpleNamespace()
    msg.content = content
    msg.group_openid = group
    msg.author = types.SimpleNamespace(member_openid=user, username="u")
    return msg


def _c2c_msg(content, user="u1"):
    msg = types.SimpleNamespace()
    msg.content = content
    msg.author = types.SimpleNamespace(user_openid=user, username="u")
    return msg


@pytest.mark.asyncio
async def test_group_ping():
    client = _make_client()
    await Dispatcher(client).route(_group_msg("<@!bot1>ping"), SCENE_GROUP_AT)
    assert client.ping_hits == 1


@pytest.mark.asyncio
async def test_group_plugin_match():
    client = _make_client(plugin_result=True)
    await Dispatcher(client).route(_group_msg("签到"), SCENE_GROUP_AT)
    assert client.plugin_hits == ["签到"]
    assert client.ai_calls == []


@pytest.mark.asyncio
async def test_group_plugin_no_match_reply():
    client = _make_client(plugin_result=False)
    await Dispatcher(client).route(_group_msg("没有这个指令"), SCENE_GROUP_AT)
    assert "未找到匹配的插件命令，发送 @机器人 /帮助 查看可用指令" in client.sent


@pytest.mark.asyncio
async def test_group_reminder_no_match_silent():
    client = _make_client(plugin_result=False)
    await Dispatcher(client).route(_group_msg("#未知"), SCENE_GROUP_AT)
    assert client.sent == []


@pytest.mark.asyncio
async def test_group_full_message_skips_affection():
    called = []

    async def try_plugins(message, order, skip_plugins=None):
        called.append(skip_plugins)
        return False

    client = _make_client()
    client.plugin_manager = types.SimpleNamespace(try_plugins=try_plugins)
    await Dispatcher(client).route(_group_msg("+foo", group="g1"), SCENE_GROUP)
    assert called == [{"affection"}]


@pytest.mark.asyncio
async def test_group_full_reminder_uses_raw_content():
    sent = []

    async def try_plugins(message, order, skip_plugins=None):
        return False

    client = _make_client()
    client.plugin_manager = types.SimpleNamespace(try_plugins=try_plugins)
    await Dispatcher(client).route(_group_msg("#未知"), SCENE_GROUP)
    assert "未找到匹配的插件命令，发送 @机器人 /帮助 查看可用指令" in client.sent
    client.sent.clear()
    await Dispatcher(client).route(_group_msg("<@!bot1> #未知"), SCENE_GROUP)
    assert client.sent == []


@pytest.mark.asyncio
async def test_c2c_ai_chat():
    client = _make_client()
    await Dispatcher(client).route(_c2c_msg("你好呀"), SCENE_C2C)
    assert client.ai_calls == [("你好呀", "u1", "用户", False)]


@pytest.mark.asyncio
async def test_c2c_logout_clears_context():
    client = _make_client()
    client.context.user_lists["u1"] = ["history"]
    await Dispatcher(client).route(_c2c_msg("注销"), SCENE_C2C)
    assert "u1" not in client.context.user_lists
    assert "已清除你的对话上下文记忆" in client.sent


@pytest.mark.asyncio
async def test_c2c_empty_greets():
    client = _make_client()
    await Dispatcher(client).route(_c2c_msg(""), SCENE_C2C)
    assert "你好呀~ 我是测试，有什么可以帮你的吗？" in client.sent


@pytest.mark.asyncio
async def test_blacklisted_user_ignored():
    client = _make_client()
    client.config = {"black_list": ["banned"]}
    await Dispatcher(client).route(_c2c_msg("ping", user="banned"), SCENE_C2C)
    assert client.ping_hits == 0
    assert client.ai_calls == []
    assert client.stats.messages == 0


@pytest.mark.asyncio
async def test_ai_disabled_reply():
    client = _make_client()
    client.allow_ai = False
    await Dispatcher(client).route(_c2c_msg("随便说点"), SCENE_C2C)
    assert "未找到相关指令" in client.sent
