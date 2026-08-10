# -*- coding: utf-8 -*-

import logging
import types
from typing import Any

import pytest

from core.dedup import MessageDedup
from core.dispatcher import Dispatcher, SCENE_C2C


def test_dedup_basic():
    dedup = MessageDedup()
    assert dedup.is_duplicate("m1") is False
    assert dedup.is_duplicate("m1") is True
    assert dedup.is_duplicate("m2") is False


def test_dedup_window_expiry():
    import time
    dedup = MessageDedup(window=0.05)
    assert dedup.is_duplicate("m1") is False
    time.sleep(0.06)
    assert dedup.is_duplicate("m1") is False


def test_dedup_max_items():
    dedup = MessageDedup(window=60, max_items=3)
    for i in range(4):
        dedup.is_duplicate(f"m{i}")
    assert dedup.is_duplicate("m0") is False
    assert dedup.is_duplicate("m3") is True


class _FakeStats:
    def __init__(self):
        self.messages = 0

    def record_nickname(self, *a):
        pass

    def record_message(self):
        self.messages += 1


class _FakeClient:
    def __init__(self):
        self.logger = logging.getLogger("test-dedup")
        self.config = {}
        self.reminder = "#"
        self.bot_name = "测试"
        self.version_name = "1.0"
        self.allow_ai = True
        self.stats = _FakeStats()
        self.context = types.SimpleNamespace(user_lists={})
        self.ping_hits = 0
        self.plugin_manager: Any = types.SimpleNamespace(try_plugins=self._noop_plugins)

    async def _noop_plugins(self, *a, **kw):
        return False

    def _try_get_nickname(self, m):
        return ""

    def _strip_mention(self, c):
        return c

    async def _handle_ping(self, m):
        self.ping_hits += 1

    async def _handle_help_command(self, m):
        pass

    async def _handle_status_command(self, m):
        pass

    async def _handle_roleplay_command(self, m, c):
        return False

    async def _send_message(self, m, *a, **kw):
        pass

    async def _send_help_image(self, m, t):
        return True

    async def _handle_ai_chat(self, m, *a, **kw):
        pass


def _msg(mid):
    msg = types.SimpleNamespace()
    msg.id = mid
    msg.content = "ping"
    msg.author = types.SimpleNamespace(user_openid="u1", username="u")
    return msg


@pytest.mark.asyncio
async def test_dispatcher_dedups_same_message_id():
    client = _FakeClient()
    dispatcher = Dispatcher(client)
    await dispatcher.route(_msg("same-id"), SCENE_C2C)
    assert client.ping_hits == 1
    await dispatcher.route(_msg("same-id"), SCENE_C2C)
    assert client.ping_hits == 1
    assert client.stats.messages == 1
