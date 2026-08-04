# -*- coding: utf-8 -*-
"""Model / 消息模型测试：属性访问、嵌套包装、reply() 路由"""

import pytest

from qqbot_openapi import (
    Channel,
    DirectMessage,
    GroupMessage,
    Guild,
    GuildMember,
    Message,
    Model,
    Reaction,
)


class FakeAPI:
    def __init__(self):
        self.calls = []

    async def post_group_message(self, **kwargs):
        self.calls.append(("group", kwargs))
        return {"ok": True}

    async def post_c2c_message(self, **kwargs):
        self.calls.append(("c2c", kwargs))
        return {"ok": True}

    async def post_channel_message(self, **kwargs):
        self.calls.append(("channel", kwargs))
        return {"ok": True}


def test_field_access():
    m = Message({"id": "123", "content": "hi", "author": {"id": "u1"}})
    assert m.id == "123"
    assert m.content == "hi"
    assert m.author.id == "u1"


def test_none_value_field_returns_none():
    m = Message({"id": "123", "content": None})
    assert m.content is None


def test_unknown_field_raises_attribute_error():
    m = Message({"id": "123"})
    with pytest.raises(AttributeError):
        _ = m.nonexistent_field


def test_get_with_default():
    m = Message({"id": "123"})
    assert m.get("content") is None
    assert m.get("content", "默认") == "默认"


def test_contains():
    m = Message({"id": "123"})
    assert "id" in m
    assert "content" not in m


def test_to_dict_unwraps_nested():
    m = Message({"id": "123", "author": {"id": "u1", "name": "x"}})
    d = m.to_dict()
    assert d == {"id": "123", "author": {"id": "u1", "name": "x"}}
    assert isinstance(d["author"], dict)


def test_setattr_extra_field():
    m = Message({"id": "123"})
    m.extra = "v"
    assert m.extra == "v"
    assert m.to_dict()["extra"] == "v"


async def test_group_message_reply_routes_to_group_api():
    api = FakeAPI()
    msg = GroupMessage({"id": "m1", "group_openid": "g1"})
    msg._set_api(api)
    await msg.reply(content="hello")
    assert api.calls[0][0] == "group"
    assert api.calls[0][1]["group_openid"] == "g1"
    assert api.calls[0][1]["msg_id"] == "m1"


async def test_channel_message_reply_routes_to_channel_api():
    api = FakeAPI()
    msg = Message({"id": "m1", "channel_id": "c1"})
    msg._set_api(api)
    await msg.reply(content="hi")
    assert api.calls[0][0] == "channel"
    assert api.calls[0][1]["channel_id"] == "c1"


async def test_c2c_message_reply_routes_to_c2c_api():
    api = FakeAPI()
    msg = GroupMessage({"id": "m1", "author": {"user_openid": "u1"}})
    msg._set_api(api)
    await msg.reply(content="hi")
    assert api.calls[0][0] == "c2c"
    assert api.calls[0][1]["openid"] == "u1"


async def test_reply_markdown_sets_msg_type_2():
    api = FakeAPI()
    msg = GroupMessage({"id": "m1", "group_openid": "g1"})
    msg._set_api(api)
    await msg.reply(markdown="## 标题")
    assert api.calls[0][1]["msg_type"] == 2


async def test_reply_without_api_raises():
    msg = GroupMessage({"id": "m1", "group_openid": "g1"})
    with pytest.raises(RuntimeError):
        await msg.reply(content="hi")


async def test_reply_no_target_raises():
    api = FakeAPI()
    msg = Model({"id": "m1"})
    msg._set_api(api)
    with pytest.raises(RuntimeError):
        await msg.reply(content="hi")


def test_specific_models_are_model_subclasses():
    for cls in (Guild, Channel, GuildMember, Reaction, DirectMessage,
                Message, GroupMessage):
        assert issubclass(cls, Model)


def test_member_alias():
    from qqbot_openapi import Member

    assert Member is GuildMember


def test_reaction_field_access():
    r = Reaction({"user_id": "u1", "channel_id": "c1",
                  "target": {"id": "m1", "type": 0}})
    assert r.user_id == "u1"
    assert r.target.id == "m1"
