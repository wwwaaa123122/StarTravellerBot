# -*- coding: utf-8 -*-

__version__ = "0.1.0"

from . import logging  # noqa: F401
from .api import API  # noqa: F401
from .auth import AccessTokenManager  # noqa: F401
from .client import Client  # noqa: F401
from .connection import ConnectionState, GatewayClient  # noqa: F401
from .errors import (  # noqa: F401
    AccessTokenError,
    APIError,
    GatewayError,
    NotSupportError,
    QQBotError,
    WebSocketClosedError,
)
from .http import HTTPClient, Route  # noqa: F401
from .intents import Intents  # noqa: F401
from .logging import get_logger  # noqa: F401
from .message import (  # noqa: F401
    Audio,
    AuditResult,
    Author,
    C2CMsgReceive,
    C2CMsgReject,
    Channel,
    DirectMessage,
    Embed,
    FriendUser,
    Group,
    GroupJoinRequest,
    GroupMessage,
    Guild,
    GuildMember,
    Interaction,
    Member,
    Message,
    MessageAudit,
    MessageReference,
    Model,
    Post,
    Reaction,
    Ready,
    Reply,
    SubscribeMessageStatus,
    SubscribeMsgTemplateResult,
    Thread,
    User,
)

__all__ = (
    "API",
    "APIError",
    "AccessTokenError",
    "AccessTokenManager",
    "AuditResult",
    "Audio",
    "Author",
    "C2CMsgReceive",
    "C2CMsgReject",
    "Channel",
    "Client",
    "ConnectionState",
    "DirectMessage",
    "Embed",
    "FriendUser",
    "GatewayClient",
    "GatewayError",
    "Group",
    "GroupJoinRequest",
    "GroupMessage",
    "Guild",
    "GuildMember",
    "HTTPClient",
    "Intents",
    "Interaction",
    "Member",
    "Message",
    "MessageAudit",
    "MessageReference",
    "Model",
    "NotSupportError",
    "Post",
    "QQBotError",
    "Reaction",
    "Ready",
    "Reply",
    "Route",
    "SubscribeMessageStatus",
    "SubscribeMsgTemplateResult",
    "Thread",
    "User",
    "WebSocketClosedError",
    "get_logger",
    "logging",
    "__version__",
)
