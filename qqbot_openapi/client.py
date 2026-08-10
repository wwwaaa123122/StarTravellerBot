# -*- coding: utf-8 -*-

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
        from .message import Model

        self.robot = Model(user)

    async def start(self, appid: str, secret: str) -> None:
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
        if self._gateway is not None:
            self._gateway.stop()
        if self._token_manager is not None:
            await self._token_manager.close()
