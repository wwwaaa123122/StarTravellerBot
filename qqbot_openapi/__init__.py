# -*- coding: utf-8 -*-
"""qqbot_openapi：QQ 开放平台机器人 SDK

基于官方文档实现的轻量封装，覆盖：
- 访问凭证管理（AppAccessToken 自动刷新）
- REST API（群聊/C2C 消息、文件、撤回）
- WebSocket 网关（心跳、Resume 重连、事件分发）
"""

__version__ = "0.1.0.dev3"

from . import logging  # noqa: F401
from .api import API  # noqa: F401
from .auth import AccessTokenManager  # noqa: F401
from .client import Client  # noqa: F401
from .connection import ConnectionState, GatewayClient  # noqa: F401
from .errors import (  # noqa: F401
    APIError,
    AccessTokenError,
    GatewayError,
    NotSupportError,
    QQBotError,
    WebSocketClosedError,
)
from .http import HTTPClient, Route  # noqa: F401
from .intents import Intents  # noqa: F401
from .logging import get_logger  # noqa: F401
from .message import (  # noqa: F401
    DirectMessage,
    FriendUser,
    Group,
    GroupMessage,
    Message,
    Model,
    Ready,
)

__all__ = (
    "API",
    "APIError",
    "AccessTokenError",
    "AccessTokenManager",
    "Client",
    "ConnectionState",
    "DirectMessage",
    "FriendUser",
    "GatewayClient",
    "GatewayError",
    "Group",
    "GroupMessage",
    "HTTPClient",
    "Intents",
    "Message",
    "Model",
    "NotSupportError",
    "QQBotError",
    "Ready",
    "Route",
    "WebSocketClosedError",
    "get_logger",
    "logging",
    "__version__",
)
