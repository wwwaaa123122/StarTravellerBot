# -*- coding: utf-8 -*-
"""网关事件订阅（Identify 的 intents 字段）

支持旧版 botpy 的两种订阅方式：构造参数方式与属性方式::

    intents = Intents(public_guild_messages=True, direct_message=True)

    intents = Intents.none()
    intents.public_guild_messages = True
    intents.direct_message = True

快捷订阅：``Intents.all()`` 订阅所有事件，``Intents.default()`` 订阅全部公域事件。
"""

__all__ = ("Intents",)

# 官方文档定义的 Intent 标志位（旧版 botpy 命名 + 新版别名）
_INTENT_FLAGS = {
    "guilds": 1 << 0,
    "guild_members": 1 << 1,
    "guild_moderation": 1 << 2,
    "guild_messages": 1 << 9,              # 频道消息（私域）
    "guild_message_reactions": 1 << 10,
    "guild_message_typing": 1 << 11,
    "direct_message": 1 << 12,             # 频道私信
    # 群聊 + C2C 单聊 + 群/好友相关事件（新版文档为 1<<25）
    "public_messages": 1 << 25,
    "group_and_c2c_event": 1 << 25,
    "interaction": 1 << 26,
    "message_audit": 1 << 27,
    "forums": 1 << 28,                     # 论坛事件（私域，旧版 botpy 命名）
    "forums_event": 1 << 28,
    "audio_action": 1 << 29,
    "public_guild_messages": 1 << 30,      # AT_MESSAGE_CREATE、PUBLIC_MESSAGE_DELETE
}


class Intents:
    """网关事件订阅集合

    支持旧版 botpy 风格的构造方式::

        intents = Intents(
            public_guild_messages=True,  # 频道 @ 消息
            public_messages=True,        # 群聊/C2C 消息
            direct_message=True,
            guilds=True,
            guild_members=True,
        )

    也支持属性式订阅::

        intents = Intents.none()
        intents.public_guild_messages = True
    """

    __slots__ = ("value",)

    # 便捷常量
    GUILDS = 1 << 0
    GUILD_MEMBERS = 1 << 1
    GUILD_MODERATION = 1 << 2
    GUILD_MESSAGES = 1 << 9
    GUILD_MESSAGE_REACTIONS = 1 << 10
    GUILD_MESSAGE_TYPING = 1 << 11
    DIRECT_MESSAGE = 1 << 12
    GROUP_AND_C2C_EVENT = 1 << 25
    INTERACTION = 1 << 26
    MESSAGE_AUDIT = 1 << 27
    FORUMS_EVENT = 1 << 28
    AUDIO_ACTION = 1 << 29
    PUBLIC_GUILD_MESSAGES = 1 << 30

    def __init__(self, **kwargs):
        value = 0
        for key, enabled in kwargs.items():
            if not enabled:
                continue
            flag = _INTENT_FLAGS.get(key)
            if flag is None:
                raise ValueError(f"未知的 Intent: {key!r}")
            value |= flag
        object.__setattr__(self, "value", value)

    # ------------------------------------------------------------------
    # 旧版 botpy 快捷订阅
    # ------------------------------------------------------------------
    @classmethod
    def none(cls) -> "Intents":
        """关闭全部订阅，再按需打开"""
        return cls()

    @classmethod
    def all(cls) -> "Intents":
        """订阅所有事件"""
        value = 0
        for flag in _INTENT_FLAGS.values():
            value |= flag
        obj = cls()
        object.__setattr__(obj, "value", value)
        return obj

    @classmethod
    def default(cls) -> "Intents":
        """订阅全部公域事件（与旧版 botpy 一致，开启 public_guild_messages）"""
        obj = cls()
        obj.public_guild_messages = True
        return obj

    # ------------------------------------------------------------------
    # 属性式订阅：intents.public_guild_messages = True
    # ------------------------------------------------------------------
    def __setattr__(self, name: str, value: bool) -> None:
        if name == "value":
            object.__setattr__(self, "value", value)
            return
        flag = _INTENT_FLAGS.get(name)
        if flag is None:
            raise AttributeError(f"未知的 Intent: {name!r}")
        current = object.__getattribute__(self, "value")
        if value:
            object.__setattr__(self, "value", current | flag)
        else:
            object.__setattr__(self, "value", current & ~flag)

    def __getattr__(self, name: str) -> bool:
        flag = _INTENT_FLAGS.get(name)
        if flag is None:
            raise AttributeError(f"{type(self).__name__!r} object has no attribute {name!r}")
        return bool(object.__getattribute__(self, "value") & flag)

    def __int__(self) -> int:
        return self.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Intents):
            return self.value == other.value
        if isinstance(other, int):
            return self.value == other
        return NotImplemented

    def __repr__(self) -> str:
        return f"<Intents value={self.value}>"
