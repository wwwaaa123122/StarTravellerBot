# -*- coding: utf-8 -*-
"""用户昵称获取测试

结论（依据官方文档）：QQ 开放平台 v2 没有「按 openid 主动查询用户昵称」的
REST 接口，昵称只能被动从消息事件中获取——事件体 ``author.username`` 字段即
「用户昵称」。本测试用官方文档结构的事件体走 SDK 分发 + 客户端提取逻辑，
验证昵称能正确取到。
"""

import pytest

from qqbot_openapi import GroupMessage, Message
from qqbot_openapi.connection import ConnectionState

USER_OPENID = "8311636DD1F88D7C4E9021CF26495EEA"

GROUP_PAYLOAD = {
    "id": "AAAA0001",
    "author": {
        "id": USER_OPENID,
        "username": "星辰旅人测试号",
        "bot": False,
        "union_openid": "",
        "union_user_account": "",
        "user_openid": "",
        "member_openid": USER_OPENID,
        "member_role": "member",
    },
    "content": "@机器人 签到",
    "group_openid": "GROUP_TEST_OPENID_1234",
    "timestamp": "2026-08-03T12:00:00+08:00",
}

C2C_PAYLOAD = {
    "id": "BBBB0002",
    "author": {
        "id": USER_OPENID,
        "username": "星辰旅人测试号",
        "bot": False,
        "user_openid": USER_OPENID,
        "member_openid": "",
    },
    "content": "你好",
    "timestamp": "2026-08-03T12:01:00+08:00",
}


class NicknameCollector:
    """模拟机器人客户端的昵称提取（与 client.XCLRClient._try_get_nickname 同逻辑）"""

    def __init__(self):
        self.extracted = []

    @staticmethod
    def _try_get_nickname(message) -> str:
        author = getattr(message, "author", None)
        if author is None:
            return ""
        for key in ("username", "member_name", "user_name"):
            try:
                value = getattr(author, key)
            except AttributeError:
                continue
            if value:
                return str(value)
        return ""

    async def on_group_at_message_create(self, message):
        self.extracted.append(self._try_get_nickname(message))

    async def on_c2c_message_create(self, message):
        self.extracted.append(self._try_get_nickname(message))


def _dispatch_to(collector, event_name, payload):
    state = ConnectionState(collector)
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(
            state.parse_message({"op": 0, "s": 1, "t": event_name, "d": payload})
        )
        if state._tasks:
            loop.run_until_complete(
                asyncio.gather(*list(state._tasks), return_exceptions=True)
            )
    finally:
        loop.close()


def test_group_event_author_has_username():
    msg = GroupMessage(GROUP_PAYLOAD)
    assert msg.author.member_openid == USER_OPENID
    assert msg.author.username == "星辰旅人测试号"


def test_c2c_event_author_has_username():
    msg = GroupMessage(C2C_PAYLOAD)
    assert msg.author.user_openid == USER_OPENID
    assert msg.author.username == "星辰旅人测试号"


def test_nickname_extract_from_group_event():
    collector = NicknameCollector()
    _dispatch_to(collector, "GROUP_AT_MESSAGE_CREATE", GROUP_PAYLOAD)
    assert collector.extracted == ["星辰旅人测试号"]


def test_nickname_extract_from_c2c_event():
    collector = NicknameCollector()
    _dispatch_to(collector, "C2C_MESSAGE_CREATE", C2C_PAYLOAD)
    assert collector.extracted == ["星辰旅人测试号"]


def test_nickname_falls_back_when_username_missing():
    msg = GroupMessage({"id": "m1", "group_openid": "g1",
                        "author": {"member_openid": USER_OPENID}})
    assert NicknameCollector._try_get_nickname(msg) == ""


def test_nickname_none_author():
    msg = Message({"id": "m1"})
    assert NicknameCollector._try_get_nickname(msg) == ""
