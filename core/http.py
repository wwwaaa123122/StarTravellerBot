# -*- coding: utf-8 -*-

import httpx

_USER_AGENT = "StarTravellerBot/3.1 (QQ OpenAPI Bot; +https://xc-lr.cn/about)"


def create_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(connect=10, read=30, write=30, pool=10),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        headers={"User-Agent": _USER_AGENT},
    )
