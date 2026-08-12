# -*- coding: utf-8 -*-

import asyncio
import inspect
import json
import platform
import time
from typing import Any, Dict, List, Literal, Optional, cast

import aiohttp

from . import logging as qq_logging
from .errors import WebSocketClosedError
from .message import (
    Audio,
    AuditResult,
    C2CMsgReceive,
    C2CMsgReject,
    Channel,
    DirectMessage,
    FriendUser,
    Group,
    GroupJoinRequest,
    GroupMessage,
    Guild,
    GuildMember,
    Interaction,
    Message,
    MessageAudit,
    Post,
    Reaction,
    Ready,
    Reply,
    SubscribeMessageStatus,
    Thread,
)

_log = qq_logging.get_logger(__name__)

OP_DISPATCH = 0
OP_HEARTBEAT = 1
OP_IDENTIFY = 2
OP_RESUME = 6
OP_RECONNECT = 7
OP_INVALID_SESSION = 9
OP_HELLO = 10
OP_HEARTBEAT_ACK = 11

INVALID_OPCODE = 4001
INVALID_PAYLOAD = 4002
NOT_AUTHENTICATED = 4003
AUTHENTICATION_FAILED = 4004
AUTH_FAILED_AFTER_IDENTIFY = 4005
INVALID_SESSION = 4006
SEQ_ERROR = 4007
RATE_LIMITED = 4008
SESSION_TIMEOUT = 4009
INVALID_SHARD = 4010
INVALID_INTENT = 4013
INTENT_NO_PERMISSION = 4014
BOT_DISABLED = 4914
BOT_BANNED = 4915

_FATAL_CODES = frozenset(
    {
        NOT_AUTHENTICATED,
        AUTHENTICATION_FAILED,
        AUTH_FAILED_AFTER_IDENTIFY,
        INVALID_SHARD,
        INVALID_INTENT,
        INTENT_NO_PERMISSION,
        BOT_DISABLED,
        BOT_BANNED,
    }
)

_EVENT_HANDLERS: Dict[str, tuple] = {
    "READY": ("on_ready", Ready),
    "C2C_MESSAGE_CREATE": ("on_c2c_message_create", GroupMessage),
    "GROUP_AT_MESSAGE_CREATE": ("on_group_at_message_create", GroupMessage),
    "GROUP_MESSAGE_CREATE": ("on_group_message_create", GroupMessage),
    "GROUP_JOIN_REQUEST": ("on_group_join_request", GroupJoinRequest),
    "GROUP_ADD_ROBOT": ("on_group_add_robot", Group),
    "GROUP_DEL_ROBOT": ("on_group_del_robot", Group),
    "GROUP_MSG_REJECT": ("on_group_msg_reject", Group),
    "GROUP_MSG_RECEIVE": ("on_group_msg_receive", Group),
    "C2C_MSG_RECEIVE": ("on_c2c_msg_receive", C2CMsgReceive),
    "C2C_MSG_REJECT": ("on_c2c_msg_reject", C2CMsgReject),
    "SUBSCRIBE_MESSAGE_STATUS": ("on_subscribe_message_status", SubscribeMessageStatus),
    "FRIEND_ADD": ("on_friend_add", FriendUser),
    "FRIEND_DEL": ("on_friend_del", FriendUser),
    "AT_MESSAGE_CREATE": ("on_at_message_create", Message),
    "PUBLIC_MESSAGE_DELETE": ("on_public_message_delete", Message),
    "MESSAGE_CREATE": ("on_message_create", Message),
    "MESSAGE_DELETE": ("on_message_delete", Message),
    "DIRECT_MESSAGE_CREATE": ("on_direct_message_create", DirectMessage),
    "DIRECT_MESSAGE_DELETE": ("on_direct_message_delete", DirectMessage),
    "MESSAGE_REACTION_ADD": ("on_message_reaction_add", Reaction),
    "MESSAGE_REACTION_REMOVE": ("on_message_reaction_remove", Reaction),
    "GUILD_CREATE": ("on_guild_create", Guild),
    "GUILD_UPDATE": ("on_guild_update", Guild),
    "GUILD_DELETE": ("on_guild_delete", Guild),
    "CHANNEL_CREATE": ("on_channel_create", Channel),
    "CHANNEL_UPDATE": ("on_channel_update", Channel),
    "CHANNEL_DELETE": ("on_channel_delete", Channel),
    "GUILD_MEMBER_ADD": ("on_guild_member_add", GuildMember),
    "GUILD_MEMBER_UPDATE": ("on_guild_member_update", GuildMember),
    "GUILD_MEMBER_REMOVE": ("on_guild_member_remove", GuildMember),
    "INTERACTION_CREATE": ("on_interaction_create", Interaction),
    "MESSAGE_AUDIT_PASS": ("on_message_audit_pass", MessageAudit),
    "MESSAGE_AUDIT_REJECT": ("on_message_audit_reject", MessageAudit),
    "FORUM_THREAD_CREATE": ("on_forum_thread_create", Thread),
    "FORUM_THREAD_UPDATE": ("on_forum_thread_update", Thread),
    "FORUM_THREAD_DELETE": ("on_forum_thread_delete", Thread),
    "FORUM_POST_CREATE": ("on_forum_post_create", Post),
    "FORUM_POST_DELETE": ("on_forum_post_delete", Post),
    "FORUM_REPLY_CREATE": ("on_forum_reply_create", Reply),
    "FORUM_REPLY_DELETE": ("on_forum_reply_delete", Reply),
    "FORUM_PUBLISH_AUDIT_RESULT": ("on_forum_publish_audit_result", AuditResult),
    "AUDIO_START": ("on_audio_start", Audio),
    "AUDIO_FINISH": ("on_audio_finish", Audio),
    "AUDIO_ON_MIC": ("on_audio_on_mic", Audio),
    "AUDIO_OFF_MIC": ("on_audio_off_mic", Audio),
}


class ConnectionState:

    def __init__(self, client: Any):
        self._client = client
        self.session_id: Optional[str] = None
        self.seq: Optional[int] = None
        self._tasks: set = set()
        self._accepts_event_cache: Dict[Any, bool] = {}

    @property
    def client(self) -> Any:
        return self._client

    async def parse_message(self, payload: Dict[str, Any]) -> None:
        seq = payload.get("s")
        if seq is not None:
            self.seq = seq

        event_name = payload.get("t") or ""
        handler = _EVENT_HANDLERS.get(event_name)
        if handler is None:
            return
        callback_name, model_cls = handler
        callback = getattr(self._client, callback_name, None)
        if callback is None:
            return

        data = payload.get("d") or {}
        event = model_cls(data)
        api = getattr(self._client, "api", None)
        if api is not None and hasattr(event, "_set_api"):
            event._set_api(api)

        if event_name == "READY":
            self.session_id = data.get("session_id")
            self._client._set_robot(data.get("user") or {})
            _log.info("网关就绪 session_id=%s shard=%s", self.session_id, data.get("shard"))

        task = asyncio.create_task(self._dispatch(callback, event))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def _accepts_event(self, callback: Any) -> bool:
        key = getattr(callback, "__func__", callback)
        cached = self._accepts_event_cache.get(key)
        if cached is not None:
            return cached
        try:
            sig = inspect.signature(callback)
            sig.bind(object())
            accepts = True
        except (TypeError, ValueError):
            accepts = False
        self._accepts_event_cache[key] = accepts
        return accepts

    async def _dispatch(self, callback: Any, event: Any) -> None:
        try:
            if self._accepts_event(callback):
                await callback(event)
            else:
                await callback()
        except asyncio.CancelledError:
            raise
        except Exception:
            _log.exception("处理事件回调异常: %s", type(event).__name__)


class GatewayClient:

    def __init__(
        self,
        wss_url: str,
        token_manager: Any,
        intents: Any,
        state: ConnectionState,
        shard: Optional[List[int]] = None,
    ):
        self._url = wss_url
        self._token_manager = token_manager
        self._intents = intents
        self._state = state
        self._shard = shard or [0, 1]
        self._heartbeat_interval = 0.0
        self._last_ack = 0.0
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._closed = False

    async def run(self) -> None:
        attempt = 0
        while not self._closed:
            try:
                close_code = await self._connect_once()
            except aiohttp.ClientError as exc:
                _log.warning("网关连接失败: %s", exc)
                close_code = None
            except (OSError, asyncio.TimeoutError) as exc:
                _log.warning("网关连接异常: %s", exc)
                close_code = None

            if close_code is not None and close_code in _FATAL_CODES:
                raise WebSocketClosedError(close_code, f"网关关闭码 {close_code} 不可自动恢复")

            if close_code == SESSION_TIMEOUT:
                _log.info("连接过期（4009），下次连接将尝试 Resume")
            elif close_code in (INVALID_SESSION, SEQ_ERROR):
                _log.info("session/seq 无效，重置后重新 Identify")
                self._state.session_id = None

            attempt += 1
            delay = min(2 ** min(attempt, 5), 30)
            _log.info("%.2fs 后重连网关（第 %d 次）", delay, attempt)
            await asyncio.sleep(delay)

    def stop(self) -> None:
        self._closed = True

    async def _connect_once(self) -> Optional[int]:
        async with aiohttp.ClientSession() as session:
            ws = await self._handshake(session)
            try:
                await self._listen(ws)
            finally:
                self._cancel_heartbeat()
            return ws.close_code

    async def _handshake(self, session: aiohttp.ClientSession) -> aiohttp.ClientWebSocketResponse[Literal[True]]:
        token = await self._token_manager.get_access_token()
        headers = {"Authorization": f"QQBot {token}"}
        ws = cast(aiohttp.ClientWebSocketResponse[Literal[True]], await session.ws_connect(
            self._url,
            headers=headers,
            heartbeat=30,
            max_msg_size=64 * 1024 * 1024,
        ))
        msg = await asyncio.wait_for(ws.receive(), timeout=15)
        payload = json.loads(msg.data)
        if payload.get("op") != OP_HELLO:
            await ws.close()
            raise RuntimeError(f"网关未返回 Hello: {payload}")
        self._heartbeat_interval = int(payload["d"]["heartbeat_interval"]) / 1000.0
        _log.debug("收到 Hello，heartbeat_interval=%.2fs", self._heartbeat_interval)

        if self._state.session_id:
            await self._send_resume(ws)
        else:
            await self._send_identify(ws)
        return ws

    async def _send_identify(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        token = await self._token_manager.get_access_token()
        payload = {
            "op": OP_IDENTIFY,
            "d": {
                "token": f"QQBot {token}",
                "intents": int(self._intents),
                "shard": self._shard,
                "properties": {
                    "os": platform.system().lower(),
                    "language": "python",
                    "bot_version": "qqbot-openapi",
                },
            },
        }
        await ws.send_str(json.dumps(payload))
        _log.info("已发送 Identify（intents=%d shard=%s）", int(self._intents), self._shard)

    async def _send_resume(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        token = await self._token_manager.get_access_token()
        payload = {
            "op": OP_RESUME,
            "d": {
                "token": f"QQBot {token}",
                "session_id": self._state.session_id,
                "seq": self._state.seq,
            },
        }
        await ws.send_str(json.dumps(payload))
        _log.info("已发送 Resume（session_id=%s seq=%s）", self._state.session_id, self._state.seq)

    async def _listen(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        self._last_ack = time.monotonic()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(ws))
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._process_message(ws, msg.data)
                elif msg.type in (
                    aiohttp.WSMsgType.CLOSED,
                    aiohttp.WSMsgType.CLOSE,
                    aiohttp.WSMsgType.ERROR,
                ):
                    _log.info("网关连接关闭: type=%s code=%s", msg.type, ws.close_code)
                    break
        finally:
            self._cancel_heartbeat()

    async def _process_message(self, ws: aiohttp.ClientWebSocketResponse, raw: str) -> None:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            _log.warning("收到无法解析的帧: %.200r", raw)
            return
        if not isinstance(payload, dict):
            _log.warning("收到非对象 JSON 帧: %.200r", raw)
            return

        op = payload.get("op")
        if op == OP_DISPATCH:
            await self._state.parse_message(payload)
        elif op == OP_HEARTBEAT:
            await self._send_heartbeat(ws)
        elif op == OP_HEARTBEAT_ACK:
            self._last_ack = time.monotonic()
        elif op == OP_RECONNECT:
            _log.info("收到 Reconnect（op7），主动断开等待重连")
            await ws.close(code=1000)
        elif op == OP_INVALID_SESSION:
            _log.warning("收到 Invalid Session（op9）")
            self._state.session_id = None
            await self._send_identify(ws)

    async def _send_heartbeat(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        payload = {"op": OP_HEARTBEAT, "d": self._state.seq}
        await ws.send_str(json.dumps(payload))
        _log.debug("发送心跳 seq=%s", self._state.seq)

    async def _heartbeat_loop(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        interval = self._heartbeat_interval or 40.0
        while True:
            await asyncio.sleep(interval)
            if ws.closed:
                return
            if time.monotonic() - self._last_ack > interval * 2 + 5:
                _log.warning("心跳 ACK 超时，主动断开连接")
                await ws.close(code=1000)
                return
            try:
                await self._send_heartbeat(ws)
            except (aiohttp.ClientError, ConnectionError):
                _log.warning("心跳发送失败，等待重连")
                return

    def _cancel_heartbeat(self) -> None:
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
