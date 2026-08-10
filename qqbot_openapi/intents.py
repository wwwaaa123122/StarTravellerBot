# -*- coding: utf-8 -*-

__all__ = ("Intents",)

_INTENT_FLAGS = {
    "guilds": 1 << 0,
    "guild_members": 1 << 1,
    "guild_moderation": 1 << 2,
    "guild_messages": 1 << 9,
    "guild_message_reactions": 1 << 10,
    "guild_message_typing": 1 << 11,
    "direct_message": 1 << 12,
    "public_messages": 1 << 25,
    "group_and_c2c_event": 1 << 25,
    "interaction": 1 << 26,
    "message_audit": 1 << 27,
    "forums": 1 << 28,
    "forums_event": 1 << 28,
    "audio_action": 1 << 29,
    "public_guild_messages": 1 << 30,
}


class Intents:

    __slots__ = ("value",)

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

    @classmethod
    def none(cls) -> "Intents":
        return cls()

    @classmethod
    def all(cls) -> "Intents":
        value = 0
        for flag in _INTENT_FLAGS.values():
            value |= flag
        obj = cls()
        object.__setattr__(obj, "value", value)
        return obj

    @classmethod
    def default(cls) -> "Intents":
        obj = cls()
        obj.public_guild_messages = True
        return obj

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
