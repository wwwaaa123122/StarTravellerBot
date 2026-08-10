# -*- coding: utf-8 -*-

import json
import logging

import pytest

from ai.providers import OpenAICompatibleProvider, GeminiProvider, create_provider


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload, ensure_ascii=False)

    def json(self):
        return self._payload


class _FakeHTTP:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    async def post(self, url, headers=None, json=None):
        self.calls.append({"url": url, "headers": headers, "json": json})
        return self.responses.pop(0)


def _config(**overrides):
    others = {
        "deepseek_key": "sk-test",
        "ai_base_url": "https://api.deepseek.com",
        "ai_model": "deepseek-chat",
        "ai_max_tokens": 100,
        "ai_temperature": 0.5,
    }
    others.update(overrides)
    return {"Others": others}


def _logger():
    return logging.getLogger("test-provider")


@pytest.mark.asyncio
async def test_openai_provider_builds_request():
    http = _FakeHTTP([_FakeResponse(200, {
        "choices": [{"message": {"content": "你好"}, "tool_calls": None}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    })])
    provider = OpenAICompatibleProvider(_config(), http, _logger())

    choice = await provider.chat([{"role": "user", "content": "hi"}])
    assert choice is not None
    assert choice["message"]["content"] == "你好"
    assert provider.get_usage()["total_tokens"] == 15

    call = http.calls[0]
    assert call["url"] == "https://api.deepseek.com/v1/chat/completions"
    assert call["headers"]["Authorization"] == "Bearer sk-test"
    assert call["json"]["model"] == "deepseek-chat"
    assert call["json"]["max_tokens"] == 100
    assert call["json"]["temperature"] == 0.5


@pytest.mark.asyncio
async def test_openai_provider_tools_passthrough():
    http = _FakeHTTP([_FakeResponse(200, {"choices": [{"message": {"content": None, "tool_calls": [{"id": "t1"}]}}]})])
    provider = OpenAICompatibleProvider(_config(), http, _logger())
    choice = await provider.chat([{"role": "user", "content": "hi"}], tools=[{"type": "function"}])
    assert choice is not None
    assert choice["message"]["tool_calls"][0]["id"] == "t1"
    assert http.calls[0]["json"]["tools"] == [{"type": "function"}]


@pytest.mark.asyncio
async def test_openai_provider_error_returns_none():
    http = _FakeHTTP([_FakeResponse(500, {"error": "boom"})])
    provider = OpenAICompatibleProvider(_config(), http, _logger())
    assert await provider.chat([{"role": "user", "content": "hi"}]) is None


@pytest.mark.asyncio
async def test_openai_provider_no_key_returns_none():
    http = _FakeHTTP([])
    provider = OpenAICompatibleProvider(_config(deepseek_key="", openai_key=""), http, _logger())
    assert await provider.chat([{"role": "user", "content": "hi"}]) is None
    assert http.calls == []


def test_create_provider_by_mode():
    config = _config()
    provider = create_provider("Ds", config, object(), _logger())
    assert isinstance(provider, OpenAICompatibleProvider)
    gemini = create_provider("GoogleGemini", config, object(), _logger())
    assert isinstance(gemini, GeminiProvider)
