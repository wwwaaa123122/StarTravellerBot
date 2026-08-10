# -*- coding: utf-8 -*-

import time
from typing import Optional

import httpx

from . import logging
from .errors import AccessTokenError

_log = logging.get_logger(__name__)

API_BASE_PROD = "https://api.sgroup.qq.com"
API_BASE_SANDBOX = "https://sandbox.api.sgroup.qq.com"

TOKEN_URL = "https://bots.qq.com/app/getAppAccessToken"

WSS_BASE_PROD = "wss://api.sgroup.qq.com/websocket"
WSS_BASE_SANDBOX = "wss://sandbox.api.sgroup.qq.com/websocket"

_REFRESH_ADVANCE = 60


class AccessTokenManager:

    def __init__(
        self,
        app_id: str,
        secret: str,
        sandbox: bool = False,
        base_url: Optional[str] = None,
        timeout: float = 10.0,
    ):
        self._app_id = app_id
        self._secret = secret
        self._base_url = (base_url or (API_BASE_SANDBOX if sandbox else API_BASE_PROD)).rstrip("/")
        self._timeout = timeout
        self._session = httpx.AsyncClient(timeout=timeout)
        self._token: Optional[str] = None
        self._expires_at: float = 0.0

    @property
    def base_url(self) -> str:
        return self._base_url

    async def get_access_token(self) -> str:
        if self._token and self._expires_at - time.time() > _REFRESH_ADVANCE:
            return self._token
        return await self.refresh()

    async def refresh(self) -> str:
        url = TOKEN_URL
        payload = {"appId": self._app_id, "clientSecret": self._secret}
        try:
            resp = await self._session.post(url, json=payload)
        except httpx.HTTPError as exc:
            raise AccessTokenError(f"请求 getAppAccessToken 失败: {exc}") from exc

        if resp.status_code >= 400:
            raise AccessTokenError(
                f"getAppAccessToken 返回 {resp.status_code}: {resp.text[:200]}"
            )

        data = resp.json()
        token = data.get("access_token")
        if not token:
            raise AccessTokenError(f"getAppAccessToken 响应缺少 access_token: {data}")

        self._token = token
        self._expires_at = time.time() + int(data.get("expires_in", 7200))
        _log.info("已获取新的 access_token，有效期 %ss", int(data.get("expires_in", 7200)))
        return token

    async def close(self) -> None:
        await self._session.aclose()
