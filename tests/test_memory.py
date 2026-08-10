# -*- coding: utf-8 -*-

import asyncio
import json
import logging
import types

import pytest

from Tools.core import BotContext
from ai.chat import AIChat
from ai.memory import MemoryManager
from ai.providers import AIProvider


class MockProvider(AIProvider):
    name = "mock"

    def __init__(self, content="用户喜欢猫，讨厌雨天。"):
        self.content = content
        self.last_usage = {}
        self.calls = 0

    async def chat(self, messages, tools=None, **kwargs):
        self.calls += 1
        return {"message": {"content": self.content, "tool_calls": None}}


def _logger():
    return logging.getLogger("test-memory")


def test_long_term_empty(tmp_path):
    mem = MemoryManager(data_dir=str(tmp_path), provider=MockProvider())
    assert mem.get_long_term("u1") == ""


@pytest.mark.asyncio
async def test_compact_writes_summary(tmp_path):
    provider = MockProvider()
    mem = MemoryManager(data_dir=str(tmp_path), provider=provider, logger=_logger())
    history = [{"role": "user", "content": "你好"}, {"role": "assistant", "content": "嗨"}]
    assert await mem.compact("u1", history) is True
    data = json.loads((tmp_path / "memories.json").read_text(encoding="utf-8"))
    assert data["u1"] == ["用户喜欢猫，讨厌雨天。"]
    assert "长期记忆" in mem.get_long_term("u1")
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_compact_skips_short_history(tmp_path):
    mem = MemoryManager(data_dir=str(tmp_path), provider=MockProvider())
    assert await mem.compact("u1", [{"role": "user", "content": "单条"}]) is False
    assert not (tmp_path / "memories.json").exists()


@pytest.mark.asyncio
async def test_compact_provider_failure(tmp_path):
    class _FailProvider:
        async def chat(self, messages, tools=None, **kwargs):
            return None

    mem = MemoryManager(data_dir=str(tmp_path), provider=_FailProvider(), logger=_logger())
    history = [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]
    assert await mem.compact("u1", history) is False


@pytest.mark.asyncio
async def test_append_history_compacts_at_20(tmp_path):
    provider = MockProvider()
    mem = MemoryManager(data_dir=str(tmp_path), provider=provider)
    from Tools.rag_memory import RAGMemory
    rag = RAGMemory(data_dir=str(tmp_path))
    chat = AIChat(
        {"Others": {}}, BotContext(), rag, None, _logger(), "测试",
        memory=mem,
    )
    for i in range(11):
        chat._append_history("u1", f"q{i}", f"a{i}")
    assert len(chat.context.user_lists["u1"]) == 10
    assert chat.context.user_lists["u1"][0]["content"] == "q6"

    for _ in range(10):
        if (tmp_path / "memories.json").exists():
            break
        await asyncio.sleep(0.05)
    data = json.loads((tmp_path / "memories.json").read_text(encoding="utf-8"))
    assert "u1" in data
    assert provider.calls >= 1
