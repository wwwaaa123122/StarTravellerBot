# -*- coding: utf-8 -*-
"""共享 HTTP 客户端：统一超时/连接池/UA，供客户端与插件复用。"""

import httpx

_USER_AGENT = "StarTravellerBot/3.1 (QQ OpenAPI Bot; +https://xc-lr.cn/about)"


def create_http_client() -> httpx.AsyncClient:
    """创建带统一超时与连接池上限的 AsyncClient。"""
    return httpx.AsyncClient(
        timeout=httpx.Timeout(connect=10, read=30, write=30, pool=10),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        headers={"User-Agent": _USER_AGENT},
    )
