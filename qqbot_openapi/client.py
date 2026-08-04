# -*- coding: utf-8 -*-
"""Client 基类

与旧版 botpy.Client 入口兼容：``client.run(appid=..., secret=...)`` 阻塞运行。
子类通过定义 ``on_xxx`` 方法接收对应网关事件（官方文档确认旧版 botpy 事件
回调仍可使用）。

群聊 / 单聊 / 好友事件：
- ``on_ready(event)``
- ``on_c2c_message_create(message)``
- ``on_group_at_message_create(message)``
- ``on_group_message_create(message)``
- ``on_group_add_robot(event)`` / ``on_group_del_robot(event)``
- ``on_group_msg_reject(event)`` / ``on_group_msg_receive(event)``
- ``on_friend_add(event)`` / ``on_friend_del(event)``

频道消息事件：
- ``on_at_message_create(message)``
- ``on_public_message_delete(message)``
- ``on_message_create(message)`` / ``on_message_delete(message)``（私域）
- ``on_direct_message_create(message)`` / ``on_direct_message_delete(message)``

频道 / 成员 / 互动事件：
- ``on_guild_create(guild)`` / ``on_guild_update(guild)`` / ``on_guild_delete(guild)``
- ``on_channel_create(channel)`` / ``on_channel_update(channel)`` / ``on_channel_delete(channel)``
- ``on_guild_member_add(member)`` / ``on_guild_member_update(member)`` / ``on_guild_member_remove(member)``
- ``on_message_reaction_add(reaction)`` / ``on_message_reaction_remove(reaction)``
- ``on_interaction_create(interaction)``

审核 / 论坛 / 音频事件：
- ``on_message_audit_pass(audit)`` / ``on_message_audit_reject(audit)``
- ``on_forum_thread_create(thread)`` / ``on_forum_thread_update(thread)`` / ``on_forum_thread_delete(thread)``
- ``on_forum_post_create(post)`` / ``on_forum_post_delete(post)``
- ``on_forum_reply_create(reply)`` / ``on_forum_reply_delete(reply)``
- ``on_forum_publish_audit_result(audit_result)``
- ``on_audio_start(audio)`` / ``on_audio_finish(audio)`` / ``on_audio_on_mic(audio)`` / ``on_audio_off_mic(audio)``
"""

import asyncio
import logging
from typing import Optional

from . import logging as qq_logging
from .api import API
from .auth import API_BASE_PROD, API_BASE_SANDBOX, WSS_BASE_PROD, WSS_BASE_SANDBOX, AccessTokenManager
from .connection import ConnectionState, GatewayClient
from .http import HTTPClient
from .intents import Intents

_log = qq_logging.get_logger(__name__)


class Client:
    """QQ 开放平台机器人客户端"""

    def __init__(
        self,
        intents: Optional[Intents] = None,
        is_sandbox: bool = False,
        log_level: Optional[int] = None,
        **kwargs,
    ):
        if log_level is not None:
            logging.getLogger().setLevel(log_level)

        self.intents = intents or Intents()
        self.is_sandbox = is_sandbox
        self.api: Optional[API] = None
        self.robot = None
        self._appid: Optional[str] = None
        self._secret: Optional[str] = None
        self._token_manager: Optional[AccessTokenManager] = None
        self._gateway: Optional[GatewayClient] = None
        self._state: Optional[ConnectionState] = None

    def _set_robot(self, user: dict) -> None:
        """网关 READY 时设置机器人自身信息"""
        from .message import Model

        self.robot = Model(user)

    # ------------------------------------------------------------------
    # 启动
    # ------------------------------------------------------------------
    async def start(self, appid: str, secret: str) -> None:
        """初始化鉴权、API 与网关连接（异步）"""
        self._appid = appid
        self._secret = secret
        base_url = API_BASE_SANDBOX if self.is_sandbox else API_BASE_PROD
        wss_url = WSS_BASE_SANDBOX if self.is_sandbox else WSS_BASE_PROD

        self._token_manager = AccessTokenManager(appid, secret, sandbox=self.is_sandbox, base_url=base_url)
        self.api = API(HTTPClient(base_url, self._token_manager))
        self._state = ConnectionState(self)
        self._gateway = GatewayClient(wss_url, self._token_manager, self.intents, self._state)

        _log.info("启动 QQ 开放平台客户端（sandbox=%s）", self.is_sandbox)
        await self._gateway.run()

    def run(self, appid: str, secret: str) -> None:
        """阻塞运行入口，与旧版 botpy ``client.run(appid, secret)`` 兼容"""
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.start(appid, secret))
        finally:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            loop.run_until_complete(
                asyncio.gather(*pending, return_exceptions=True)
            ) if pending else None
            loop.close()

    async def close(self) -> None:
        """释放网络资源（token 管理器、HTTP 会话）"""
        if self._gateway is not None:
            self._gateway.stop()
        if self._token_manager is not None:
            await self._token_manager.close()
