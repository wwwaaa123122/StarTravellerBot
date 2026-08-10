# -*- coding: utf-8 -*-

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from qqbot_openapi.errors import APIError
from qqbot_openapi.http import HTTPClient, Route


def test_route_url_fills_parameters():
    route = Route("POST", "/v2/groups/{group_openid}/messages/{message_id}/recall",
                  group_openid="g1", message_id="m1")
    assert route.url == "/v2/groups/g1/messages/m1/recall"
    assert route.method == "POST"
    assert "groups/g1" in repr(route)


def _make_http(handler):
    token_mgr = SimpleNamespace(
        get_access_token=AsyncMock(return_value="tok"),
        refresh=AsyncMock(return_value="newtok"),
    )
    client = HTTPClient("https://api.test", token_mgr)
    client._session = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), timeout=5
    )
    return client, token_mgr


async def test_request_sends_auth_header():
    captured = {}

    def handler(request):
        captured["auth"] = request.headers.get("Authorization")
        captured["ct"] = request.headers.get("Content-Type")
        return httpx.Response(200, json={"code": 0})

    client, _ = _make_http(handler)
    await client.request(Route("GET", "/v2/me"))
    assert captured["auth"] == "QQBot tok"
    assert captured["ct"] == "application/json"


async def test_request_parses_json():
    def handler(request):
        return httpx.Response(200, json={"code": 0, "data": "x"})

    client, _ = _make_http(handler)
    result = await client.request(Route("GET", "/v2/me"))
    assert result == {"code": 0, "data": "x"}


async def test_request_401_retries_with_fresh_token():
    seq = {"n": 0}

    def handler(request):
        seq["n"] += 1
        if seq["n"] == 1:
            return httpx.Response(401, json={"code": 401})
        assert request.headers["Authorization"] == "QQBot newtok"
        return httpx.Response(200, json={"code": 0})

    client, token_mgr = _make_http(handler)
    result = await client.request(Route("GET", "/v2/me"))
    assert result == {"code": 0}
    token_mgr.refresh.assert_awaited_once()


async def test_request_raises_api_error():
    def handler(request):
        return httpx.Response(
            400, json={"code": 20002, "message": "bad", "request_id": "r1"}
        )

    client, _ = _make_http(handler)
    with pytest.raises(APIError) as excinfo:
        await client.request(Route("POST", "/v2/groups/g1/messages"))
    assert excinfo.value.code == 20002
    assert excinfo.value.request_id == "r1"


async def test_request_raises_api_error_non_json():
    def handler(request):
        return httpx.Response(500, text="internal error")

    client, _ = _make_http(handler)
    with pytest.raises(APIError) as excinfo:
        await client.request(Route("GET", "/v2/me"))
    assert excinfo.value.code == 500


async def test_request_passes_json_body():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={})

    client, _ = _make_http(handler)
    await client.request(Route("POST", "/v2/groups/g1/messages"),
                         json={"content": "hi"})
    assert seen["body"] == {"content": "hi"}
