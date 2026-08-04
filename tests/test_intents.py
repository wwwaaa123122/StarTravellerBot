# -*- coding: utf-8 -*-
"""Intents 订阅测试：构造参数 / 属性式 / 快捷订阅 / 未知 intent"""

import pytest

from qqbot_openapi import Intents

PGM = 1 << 30  # public_guild_messages
GM = 1 << 9    # guild_messages
DM = 1 << 12   # direct_message
GUILDS = 1 << 0
MEMBERS = 1 << 1
FORUMS = 1 << 28
GROUP = 1 << 25


def test_constructor_kwargs():
    intents = Intents(public_guild_messages=True, direct_message=True)
    assert int(intents) == PGM | DM


def test_false_kwargs_ignored():
    assert int(Intents(public_guild_messages=False)) == 0


def test_unknown_kwarg_raises():
    with pytest.raises(ValueError):
        Intents(not_an_intent=True)


def test_none():
    assert int(Intents.none()) == 0


def test_all():
    assert int(Intents.all()) == sum(set(_v for _v in (v for v in (
        1 << 0, 1 << 1, 1 << 2, 1 << 9, 1 << 10, 1 << 11, 1 << 12,
        1 << 25, 1 << 26, 1 << 27, 1 << 28, 1 << 29, 1 << 30,
    ))))


def test_all_includes_each_flag():
    value = int(Intents.all())
    for shift in (0, 1, 2, 9, 10, 11, 12, 25, 26, 27, 28, 29, 30):
        assert value & (1 << shift)


def test_default_matches_botpy_public_guild_messages():
    assert int(Intents.default()) == PGM


def test_attribute_subscription_style():
    intents = Intents.none()
    intents.public_guild_messages = True
    intents.guild_messages = True
    assert int(intents) == PGM | GM
    assert intents.public_guild_messages is True
    assert intents.guild_messages is True
    assert intents.direct_message is False


def test_attribute_disable():
    intents = Intents(public_guild_messages=True, direct_message=True)
    intents.public_guild_messages = False
    assert int(intents) == DM


def test_unknown_attribute_raises():
    intents = Intents.none()
    with pytest.raises(AttributeError):
        intents.no_such_intent = True
    with pytest.raises(AttributeError):
        _ = intents.no_such_intent


def test_forums_alias():
    assert int(Intents(forums=True)) == FORUMS
    intents = Intents.none()
    intents.forums = True
    assert int(intents) == FORUMS


def test_group_alias():
    assert int(Intents(public_messages=True)) == GROUP
    assert int(Intents(group_and_c2c_event=True)) == GROUP


def test_equality():
    assert Intents(public_guild_messages=True) == Intents(public_guild_messages=True)
    assert Intents() == 0
    assert Intents() != Intents(public_guild_messages=True)


def test_repr():
    assert "Intents" in repr(Intents.none())
