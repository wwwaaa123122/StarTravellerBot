# -*- coding: utf-8 -*-
"""网关事件订阅（Identify 的 intents 字段）"""

__all__ = ("Intents",)

# 官方文档定义的 Intent 标志位
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
    "forums_event": 1 << 28,               # 论坛事件（私域）
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
    """

    __slots__ = ("value",)

    # 便捷常量
    GUILDS = 1 << 0
    GUILD_MEMBERS = 1 << 1
    GUILD_MODERATION = 1 << 2
    GUILD_MESSAGES = 1 << 9
    GUILD_MESSAGE_REACTIONS = 1 << 10
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
        self.value = value

    def __int__(self) -> int:
        return self.value

    def __repr__(self) -> str:
        return f"<Intents value={self.value}>"
