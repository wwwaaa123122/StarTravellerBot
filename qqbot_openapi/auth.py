# -*- coding: utf-8 -*-
"""访问凭证（AppAccessToken）管理与环境域名"""

import time
from typing import Optional

import httpx

from . import logging
from .errors import AccessTokenError

_log = logging.get_logger(__name__)

# 开放平台 API 域名
API_BASE_PROD = "https://api.sgroup.qq.com"
API_BASE_SANDBOX = "https://sandbox.api.sgroup.qq.com"

# 获取 AppAccessToken 的固定域名（与业务 API 域名不同，不区分沙箱/正式）
TOKEN_URL = "https://bots.qq.com/app/getAppAccessToken"

# WebSocket 网关地址
WSS_BASE_PROD = "wss://api.sgroup.qq.com/websocket"
WSS_BASE_SANDBOX = "wss://sandbox.api.sgroup.qq.com/websocket"

# Token 过期前提前刷新的余量（秒）
_REFRESH_ADVANCE = 60


class AccessTokenManager:
    """获取并自动刷新 AppAccessToken

    首次调用 :meth:`get_access_token` 时向 ``/app/getAppAccessToken`` 申请，
    过期前复用缓存，避免每次请求都走鉴权接口。
    """

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
        """返回有效的 access_token，必要时自动刷新"""
        if self._token and self._expires_at - time.time() > _REFRESH_ADVANCE:
            return self._token
        return await self.refresh()

    async def refresh(self) -> str:
        """强制向开放平台申请新的 access_token"""
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
        # expires_in 单位：秒
        self._expires_at = time.time() + int(data.get("expires_in", 7200))
        _log.info("已获取新的 access_token，有效期 %ss", int(data.get("expires_in", 7200)))
        return token

    async def close(self) -> None:
        await self._session.aclose()
