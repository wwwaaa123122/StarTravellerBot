# -*- coding: utf-8 -*-

from typing import Any, Dict, Optional

import httpx

from . import logging
from .errors import APIError

_log = logging.get_logger(__name__)


class Route:

    __slots__ = ("method", "path", "parameters")

    def __init__(self, method: str, path: str, **parameters: Any):
        self.method = method
        self.path = path
        self.parameters = parameters

    @property
    def url(self) -> str:
        path = self.path
        for key, value in self.parameters.items():
            path = path.replace("{" + key + "}", str(value))
        return path

    def __repr__(self) -> str:
        return f"<Route {self.method} {self.url}>"


class HTTPClient:

    def __init__(self, base_url: str, token_manager: Any, timeout: float = 60.0):
        self._base_url = base_url.rstrip("/")
        self._token_manager = token_manager
        self._session = httpx.AsyncClient(timeout=timeout)

    @property
    def session(self) -> httpx.AsyncClient:
        return self._session

    async def request(self, route: Route, **kwargs: Any) -> Any:
        headers = dict(kwargs.pop("headers", {}) or {})
        headers.setdefault("Content-Type", "application/json")
        url = self._base_url + route.url

        token = await self._token_manager.get_access_token()
        headers.setdefault("Authorization", f"QQBot {token}")
        resp = await self._session.request(route.method, url, headers=headers, **kwargs)

        if resp.status_code == 401:
            _log.warning("请求 %s 返回 401，刷新 token 后重试", url)
            token = await self._token_manager.refresh()
            headers["Authorization"] = f"QQBot {token}"
            resp = await self._session.request(route.method, url, headers=headers, **kwargs)

        return self._process_response(route, resp)

    def _process_response(self, route: Route, resp: httpx.Response) -> Any:
        try:
            data = resp.json()
        except ValueError:
            data = None

        if resp.status_code >= 400:
            if isinstance(data, dict):
                code = data.get("code", resp.status_code)
                message = data.get("message", resp.text)
                request_id = data.get("request_id", "")
            else:
                code, message, request_id = resp.status_code, resp.text, ""
            raise APIError(code, message, request_id)
        return data

    async def close(self) -> None:
        await self._session.aclose()
