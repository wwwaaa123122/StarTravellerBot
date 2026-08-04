# -*- coding: utf-8 -*-
"""API 封装测试：路由与请求体构造（mock HTTPClient）"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from qqbot_openapi import API
from qqbot_openapi.http import Route


@pytest.fixture
def api():
    mock_http = MagicMock()
    mock_http.request = AsyncMock(return_value={"ok": True})
    return API(mock_http), mock_http


async def test_post_group_message(api):
    client, mock_http = api
    await client.post_group_message(
        group_openid="g1", msg_type=0, content="hello", msg_id="m1",
        msg_seq=123,
    )
    route, kwargs = mock_http.request.call_args[0][0], mock_http.request.call_args[1]
    assert isinstance(route, Route)
    assert route.url == "/v2/groups/g1/messages"
    assert kwargs["json"]["group_openid"] == "g1"
    assert kwargs["json"]["content"] == "hello"
    assert kwargs["json"]["msg_seq"] == 123


async def test_post_group_message_markdown(api):
    client, mock_http = api
    await client.post_group_message(group_openid="g1", msg_type=2,
                                    markdown={"content": "## hi"})
    body = mock_http.request.call_args[1]["json"]
    assert body["msg_type"] == 2
    assert body["markdown"] == {"content": "## hi"}


async def test_post_group_message_markdown_str(api):
    client, mock_http = api
    await client.post_group_message(group_openid="g1", markdown="## hi")
    body = mock_http.request.call_args[1]["json"]
    assert body["markdown"] == {"content": "## hi"}


async def test_post_c2c_message(api):
    client, mock_http = api
    await client.post_c2c_message(openid="u1", content="hi", msg_id="m1")
    route = mock_http.request.call_args[0][0]
    assert route.url == "/v2/users/u1/messages"
    assert mock_http.request.call_args[1]["json"]["openid"] == "u1"


async def test_post_channel_message(api):
    client, mock_http = api
    await client.post_channel_message(channel_id="c1", content="hi", msg_id="m1")
    route = mock_http.request.call_args[0][0]
    assert route.url == "/channels/c1/messages"
    assert mock_http.request.call_args[1]["json"]["msg_id"] == "m1"


async def test_post_group_file_url(api):
    client, mock_http = api
    await client.post_group_file(group_openid="g1", file_type=1,
                                 url="https://example.com/a.png")
    body = mock_http.request.call_args[1]["json"]
    assert body["url"] == "https://example.com/a.png"
    assert "file_data" not in body


async def test_post_group_file_base64(api):
    client, mock_http = api
    await client.post_group_file(group_openid="g1", file_type=1,
                                 url="data:image/png;base64,AAAA")
    body = mock_http.request.call_args[1]["json"]
    assert body["file_data"] == "AAAA"
    assert "url" not in body


async def test_post_c2c_file(api):
    client, mock_http = api
    await client.post_c2c_file(openid="u1", file_type=1,
                               url="https://example.com/a.png")
    route = mock_http.request.call_args[0][0]
    assert route.url == "/v2/users/u1/files"


async def test_delete_message_group(api):
    client, mock_http = api
    await client.delete_message(message_id="m1", group_openid="g1")
    route = mock_http.request.call_args[0][0]
    assert route.url == "/v2/groups/g1/messages/m1/recall"


async def test_delete_message_c2c(api):
    client, mock_http = api
    await client.delete_message(message_id="m1", openid="u1")
    route = mock_http.request.call_args[0][0]
    assert route.url == "/v2/users/u1/messages/m1/recall"


async def test_delete_message_requires_target(api):
    client, mock_http = api
    with pytest.raises(ValueError):
        await client.delete_message(message_id="m1")


async def test_botpy_aliases(api):
    client, mock_http = api
    assert client.post_group_recall.__func__ is client.delete_message.__func__
    assert client.post_c2c_recall.__func__ is client.delete_message.__func__
