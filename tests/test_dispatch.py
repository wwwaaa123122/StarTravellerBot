# -*- coding: utf-8 -*-
"""网关事件分发测试：验证旧版 botpy 事件名 → 回调 + 模型映射"""

import asyncio

import pytest

from qqbot_openapi import (
    AuditResult,
    Audio,
    Channel,
    DirectMessage,
    FriendUser,
    Group,
    GroupMessage,
    Guild,
    GuildMember,
    Interaction,
    Message,
    MessageAudit,
    Post,
    Reaction,
    Ready,
    Reply,
    Thread,
)
from qqbot_openapi.connection import ConnectionState, _EVENT_HANDLERS


def _run_state(state, payload):
    """在独立事件循环中完成 parse_message + 等待回调任务，避免跨循环调度"""
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(state.parse_message(payload))
        if state._tasks:
            loop.run_until_complete(
                asyncio.gather(*list(state._tasks), return_exceptions=True)
            )
    finally:
        loop.close()


def _make_handler(name):
    async def handler(self, event):
        self.calls.append((name, event))
    handler.__name__ = name
    return handler


class FakeClient:
    def __init__(self):
        self.calls = []
        self.robot = None
        self.api = None

    def _set_robot(self, user):
        self.robot = user


for _cb_name in {cb for cb, _ in _EVENT_HANDLERS.values()}:
    setattr(FakeClient, _cb_name, _make_handler(_cb_name))


def _dispatch(event_name: str, data: dict):
    client = FakeClient()
    state = ConnectionState(client)
    _run_state(state, {"op": 0, "s": 1, "t": event_name, "d": data})
    return client


# 事件名 → (模型类, 回调名, 样例数据)
_EVENT_CASES = [
    ("C2C_MESSAGE_CREATE", GroupMessage, "on_c2c_message_create",
     {"id": "m1", "group_openid": "g1", "author": {"user_openid": "u1"}}),
    ("GROUP_AT_MESSAGE_CREATE", GroupMessage, "on_group_at_message_create",
     {"id": "m1", "group_openid": "g1", "author": {"member_openid": "u1"}}),
    ("GROUP_MESSAGE_CREATE", GroupMessage, "on_group_message_create",
     {"id": "m1", "group_openid": "g1", "author": {"member_openid": "u1"}}),
    ("AT_MESSAGE_CREATE", Message, "on_at_message_create",
     {"id": "m1", "channel_id": "c1", "content": "hi", "author": {"id": "u1"}}),
    ("PUBLIC_MESSAGE_DELETE", Message, "on_public_message_delete",
     {"id": "m1", "channel_id": "c1"}),
    ("MESSAGE_CREATE", Message, "on_message_create",
     {"id": "m1", "channel_id": "c1", "content": "hi"}),
    ("MESSAGE_DELETE", Message, "on_message_delete",
     {"id": "m1", "channel_id": "c1"}),
    ("DIRECT_MESSAGE_CREATE", DirectMessage, "on_direct_message_create",
     {"id": "m1", "channel_id": "c1", "content": "hi"}),
    ("DIRECT_MESSAGE_DELETE", DirectMessage, "on_direct_message_delete",
     {"id": "m1", "channel_id": "c1"}),
    ("MESSAGE_REACTION_ADD", Reaction, "on_message_reaction_add",
     {"user_id": "u1", "channel_id": "c1", "target": {"id": "m1", "type": 0}}),
    ("MESSAGE_REACTION_REMOVE", Reaction, "on_message_reaction_remove",
     {"user_id": "u1", "channel_id": "c1", "target": {"id": "m1", "type": 0}}),
    ("GUILD_CREATE", Guild, "on_guild_create", {"id": "g1", "name": "频道"}),
    ("GUILD_UPDATE", Guild, "on_guild_update", {"id": "g1", "name": "频道"}),
    ("GUILD_DELETE", Guild, "on_guild_delete", {"id": "g1"}),
    ("CHANNEL_CREATE", Channel, "on_channel_create", {"id": "c1", "name": "子频道"}),
    ("CHANNEL_UPDATE", Channel, "on_channel_update", {"id": "c1", "name": "子频道"}),
    ("CHANNEL_DELETE", Channel, "on_channel_delete", {"id": "c1"}),
    ("GUILD_MEMBER_ADD", GuildMember, "on_guild_member_add",
     {"guild_id": "g1", "user": {"id": "u1"}}),
    ("GUILD_MEMBER_UPDATE", GuildMember, "on_guild_member_update",
     {"guild_id": "g1", "user": {"id": "u1"}}),
    ("GUILD_MEMBER_REMOVE", GuildMember, "on_guild_member_remove",
     {"guild_id": "g1", "user": {"id": "u1"}}),
    ("INTERACTION_CREATE", Interaction, "on_interaction_create",
     {"id": "i1", "type": 1}),
    ("MESSAGE_AUDIT_PASS", MessageAudit, "on_message_audit_pass",
     {"audit_id": "a1", "message_id": "m1"}),
    ("MESSAGE_AUDIT_REJECT", MessageAudit, "on_message_audit_reject",
     {"audit_id": "a1", "message_id": "m1"}),
    ("FORUM_THREAD_CREATE", Thread, "on_forum_thread_create",
     {"guild_id": "g1", "channel_id": "c1"}),
    ("FORUM_THREAD_UPDATE", Thread, "on_forum_thread_update",
     {"guild_id": "g1", "channel_id": "c1"}),
    ("FORUM_THREAD_DELETE", Thread, "on_forum_thread_delete",
     {"guild_id": "g1", "channel_id": "c1"}),
    ("FORUM_POST_CREATE", Post, "on_forum_post_create",
     {"guild_id": "g1", "channel_id": "c1"}),
    ("FORUM_POST_DELETE", Post, "on_forum_post_delete",
     {"guild_id": "g1", "channel_id": "c1"}),
    ("FORUM_REPLY_CREATE", Reply, "on_forum_reply_create",
     {"guild_id": "g1", "channel_id": "c1"}),
    ("FORUM_REPLY_DELETE", Reply, "on_forum_reply_delete",
     {"guild_id": "g1", "channel_id": "c1"}),
    ("FORUM_PUBLISH_AUDIT_RESULT", AuditResult, "on_forum_publish_audit_result",
     {"guild_id": "g1", "channel_id": "c1", "author_id": "u1"}),
    ("AUDIO_START", Audio, "on_audio_start", {"channel_id": "c1"}),
    ("AUDIO_FINISH", Audio, "on_audio_finish", {"channel_id": "c1"}),
    ("AUDIO_ON_MIC", Audio, "on_audio_on_mic", {"channel_id": "c1"}),
    ("AUDIO_OFF_MIC", Audio, "on_audio_off_mic", {"channel_id": "c1"}),
    ("GROUP_ADD_ROBOT", Group, "on_group_add_robot", {"group_openid": "g1"}),
    ("GROUP_DEL_ROBOT", Group, "on_group_del_robot", {"group_openid": "g1"}),
    ("GROUP_MSG_REJECT", Group, "on_group_msg_reject", {"group_openid": "g1"}),
    ("GROUP_MSG_RECEIVE", Group, "on_group_msg_receive", {"group_openid": "g1"}),
    ("FRIEND_ADD", FriendUser, "on_friend_add", {"openid": "u1"}),
    ("FRIEND_DEL", FriendUser, "on_friend_del", {"openid": "u1"}),
]


@pytest.mark.parametrize(
    "event_name, model_cls, callback, data",
    _EVENT_CASES,
    ids=[case[0] for case in _EVENT_CASES],
)
def test_dispatch_event(event_name, model_cls, callback, data):
    client = _dispatch(event_name, data)
    assert len(client.calls) == 1
    name, event = client.calls[0]
    assert name == callback
    assert isinstance(event, model_cls)


def test_dispatch_ready_sets_session_and_robot():
    client = FakeClient()
    state = ConnectionState(client)
    data = {"session_id": "s1", "user": {"id": "bot1"}, "shard": [0, 1]}
    _run_state(state, {"op": 0, "s": 1, "t": "READY", "d": data})
    assert state.session_id == "s1"
    assert client.robot == {"id": "bot1"}
    assert client.calls[0][0] == "on_ready"


def test_dispatch_unknown_event_is_noop():
    client = _dispatch("UNKNOWN_EVENT", {})
    assert client.calls == []


def test_dispatch_missing_callback_is_noop():
    class NoAudioClient(FakeClient):
        on_audio_start = None  # 遮蔽回调，等价于未定义

    client = NoAudioClient()
    state = ConnectionState(client)
    _run_state(state, {"op": 0, "s": 1, "t": "AUDIO_START", "d": {}})
    assert client.calls == []


def test_dispatch_tracks_seq():
    client = FakeClient()
    state = ConnectionState(client)
    _run_state(state, {"op": 0, "s": 42, "t": "UNKNOWN", "d": {}})
    assert state.seq == 42


class NoArgReadyClient(FakeClient):
    async def on_ready(self):
        self.calls.append(("on_ready", None))


def test_noarg_callback_compat():
    client = NoArgReadyClient()
    state = ConnectionState(client)
    _run_state(state, {"op": 0, "s": 1, "t": "READY", "d": {}})
    assert client.calls == [("on_ready", None)]


def test_dispatch_error_is_caught_and_logged():
    class BoomClient(FakeClient):
        async def on_at_message_create(self, event):
            raise RuntimeError("boom")

    client = BoomClient()
    state = ConnectionState(client)
    _run_state(state, {"op": 0, "s": 1, "t": "AT_MESSAGE_CREATE", "d": {}})
    assert client.calls == []


def test_event_handler_map_is_complete():
    """所有旧版 botpy 事件回调均已在映射中"""
    expected = {
        "on_ready", "on_at_message_create", "on_public_message_delete",
        "on_message_create", "on_message_delete", "on_direct_message_create",
        "on_direct_message_delete", "on_message_reaction_add",
        "on_message_reaction_remove", "on_guild_create", "on_guild_update",
        "on_guild_delete", "on_channel_create", "on_channel_update",
        "on_channel_delete", "on_guild_member_add", "on_guild_member_update",
        "on_guild_member_remove", "on_interaction_create",
        "on_message_audit_pass", "on_message_audit_reject",
        "on_forum_thread_create", "on_forum_thread_update",
        "on_forum_thread_delete", "on_forum_post_create",
        "on_forum_post_delete", "on_forum_reply_create",
        "on_forum_reply_delete", "on_forum_publish_audit_result",
        "on_audio_start", "on_audio_finish", "on_audio_on_mic",
        "on_audio_off_mic",
    }
    actual = {cb for cb, _ in _EVENT_HANDLERS.values()}
    assert expected <= actual


def test_ready_model_export():
    assert Ready is not None
