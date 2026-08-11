# -*- coding: utf-8 -*-

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


async def test_post_group_message_force_verify_image_resource(api):
    client, mock_http = api
    await client.post_group_message(
        group_openid="g1", markdown="## hi", force_verify_image_resource=True,
    )
    body = mock_http.request.call_args[1]["json"]
    assert body["markdown"] == {"content": "## hi", "force_verify_image_resource": True}


async def test_post_c2c_message_force_verify_image_resource(api):
    client, mock_http = api
    await client.post_c2c_message(
        openid="u1", markdown={"content": "hi"}, force_verify_image_resource=False,
    )
    body = mock_http.request.call_args[1]["json"]
    assert body["markdown"] == {"content": "hi", "force_verify_image_resource": False}


async def test_get_group_restrict_chat_setting(api):
    client, mock_http = api
    await client.get_group_restrict_chat_setting(group_openid="g1")
    route = mock_http.request.call_args[0][0]
    assert route.method == "GET"
    assert route.url == "/v2/groups/g1/restrict_chat_setting"


async def test_set_group_restrict_chat_setting(api):
    client, mock_http = api
    await client.set_group_restrict_chat_setting(
        group_openid="g1",
        members=[{"op": "add", "member_openid": "m1", "mute_expire_at": "2026-08-11T00:00:00+08:00"}],
    )
    route, kwargs = mock_http.request.call_args[0][0], mock_http.request.call_args[1]
    assert route.url == "/v2/groups/g1/restrict_chat_setting"
    assert kwargs["json"]["members"][0]["op"] == "add"


async def test_get_group_join_request_list(api):
    client, mock_http = api
    await client.get_group_join_request_list(group_openid="g1", cursor="abc", limit=20)
    route, kwargs = mock_http.request.call_args[0][0], mock_http.request.call_args[1]
    assert route.url == "/v2/groups/g1/join_request_list"
    assert kwargs["params"] == {"cursor": "abc", "limit": 20}


async def test_approval_join_request(api):
    client, mock_http = api
    await client.approval_join_request(
        group_openid="g1", member_openid="m1", op="approve",
        join_request_id="jr1", reject_reason="", add_to_member_blacklist=False,
    )
    route, kwargs = mock_http.request.call_args[0][0], mock_http.request.call_args[1]
    assert route.url == "/v2/groups/g1/approval_join_request/m1"
    assert kwargs["json"]["op"] == "approve"
    assert kwargs["json"]["join_request_id"] == "jr1"


async def test_get_join_approval_strategies(api):
    client, mock_http = api
    await client.get_join_approval_strategies(limit=10)
    route, kwargs = mock_http.request.call_args[0][0], mock_http.request.call_args[1]
    assert route.url == "/v2/groups/join_approval_strategy"
    assert kwargs["params"] == {"limit": 10}


async def test_create_join_approval_strategy(api):
    client, mock_http = api
    await client.create_join_approval_strategy(
        group_ids=[123456], is_enable="on", remark="auto pass",
    )
    route, kwargs = mock_http.request.call_args[0][0], mock_http.request.call_args[1]
    assert route.url == "/v2/groups/join_approval_strategy"
    assert kwargs["json"]["group_ids"] == [123456]
    assert kwargs["json"]["remark"] == "auto pass"


async def test_update_join_approval_strategy(api):
    client, mock_http = api
    await client.update_join_approval_strategy(
        strategy_id="st_1", is_enable="off",
        group_action={"op": "del", "group_openids": ["g2"]},
    )
    route, kwargs = mock_http.request.call_args[0][0], mock_http.request.call_args[1]
    assert route.method == "PATCH"
    assert route.url == "/v2/groups/join_approval_strategy/st_1"
    assert kwargs["json"]["group_action"]["op"] == "del"


async def test_execute_join_approval_strategy(api):
    client, mock_http = api
    await client.execute_join_approval_strategy(strategy_id="st_1")
    route = mock_http.request.call_args[0][0]
    assert route.url == "/v2/groups/join_approval_strategy/st_1/execute"


async def test_update_join_approval_strategy_whitelist(api):
    client, mock_http = api
    await client.update_join_approval_strategy_whitelist(
        strategy_id="st_1", op="add", whitelist_users=["10001", "10002"],
    )
    route, kwargs = mock_http.request.call_args[0][0], mock_http.request.call_args[1]
    assert route.url == "/v2/groups/join_approval_strategy/st_1/whitelist_users"
    assert kwargs["json"] == {"op": "add", "whitelist_users": ["10001", "10002"]}


async def test_delete_join_approval_strategy(api):
    client, mock_http = api
    await client.delete_join_approval_strategy(strategy_id="st_1")
    route = mock_http.request.call_args[0][0]
    assert route.method == "DELETE"
    assert route.url == "/v2/groups/join_approval_strategy/st_1"
