# -*- coding: utf-8 -*-
"""开放平台 REST API 客户端

提供群聊 / C2C 单聊的消息发送、文件发送与消息撤回接口。
方法签名与旧版 botpy 的 ``self.api`` 保持兼容。
"""

from typing import Any, Dict, List, Optional, Union

from . import logging
from .http import HTTPClient, Route

_log = logging.get_logger(__name__)

_MSG_TYPE_TEXT = 0
_MSG_TYPE_MARKDOWN = 2


def _resolve_file_source(value: str) -> Dict[str, str]:
    """识别文件/图片输入是 URL 还是 base64，返回 files 接口对应字段

    - ``http(s)://`` 开头 -> 公网地址，走 ``url`` 字段
    - ``data:<mime>;base64,<data>`` 或纯 base64 字符串 -> 走 ``file_data`` 字段
    """
    value = (value or "").strip()
    if value.startswith(("http://", "https://")):
        return {"url": value}
    if value.startswith("data:") and ";base64," in value:
        value = value.split(";base64,", 1)[1]
    return {"file_data": value}


def _build_markdown(markdown: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """markdown 参数兼容 str 与 dict 两种传法"""
    if isinstance(markdown, str):
        return {"content": markdown}
    return markdown


class API:
    """QQ 开放平台 API"""

    def __init__(self, http_client: HTTPClient):
        self._http = http_client

    # ------------------------------------------------------------------
    # 群聊消息
    # ------------------------------------------------------------------
    async def post_group_message(
        self,
        group_openid: str,
        msg_type: int = _MSG_TYPE_TEXT,
        msg_id: str = "",
        msg_seq: Optional[int] = None,
        content: Optional[str] = None,
        markdown: Optional[Union[str, Dict[str, Any]]] = None,
        keyboard: Optional[Dict[str, Any]] = None,
        ark: Optional[Dict[str, Any]] = None,
        message_reference: Optional[Dict[str, Any]] = None,
        msg_elements: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """发送群聊消息（POST /v2/groups/{group_openid}/messages）"""
        payload: Dict[str, Any] = {
            "group_openid": group_openid,
            "msg_type": msg_type,
            "msg_id": msg_id,
        }
        if msg_seq is not None:
            payload["msg_seq"] = msg_seq
        if content is not None:
            payload["content"] = content
        if markdown is not None:
            payload["markdown"] = _build_markdown(markdown)
        if keyboard is not None:
            payload["keyboard"] = keyboard
        if ark is not None:
            payload["ark"] = ark
        if message_reference is not None:
            payload["message_reference"] = message_reference
        if msg_elements is not None:
            payload["msg_elements"] = msg_elements
        return await self._http.request(
            Route("POST", "/v2/groups/{group_openid}/messages", group_openid=group_openid),
            json=payload,
        )

    # ------------------------------------------------------------------
    # C2C 单聊消息
    # ------------------------------------------------------------------
    async def post_c2c_message(
        self,
        openid: str,
        msg_type: int = _MSG_TYPE_TEXT,
        msg_id: str = "",
        content: Optional[str] = None,
        markdown: Optional[Union[str, Dict[str, Any]]] = None,
        keyboard: Optional[Dict[str, Any]] = None,
        ark: Optional[Dict[str, Any]] = None,
        message_reference: Optional[Dict[str, Any]] = None,
        msg_elements: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """发送 C2C 单聊消息（POST /v2/users/{openid}/messages）"""
        payload: Dict[str, Any] = {
            "openid": openid,
            "msg_type": msg_type,
            "msg_id": msg_id,
        }
        if content is not None:
            payload["content"] = content
        if markdown is not None:
            payload["markdown"] = _build_markdown(markdown)
        if keyboard is not None:
            payload["keyboard"] = keyboard
        if ark is not None:
            payload["ark"] = ark
        if message_reference is not None:
            payload["message_reference"] = message_reference
        if msg_elements is not None:
            payload["msg_elements"] = msg_elements
        return await self._http.request(
            Route("POST", "/v2/users/{openid}/messages", openid=openid),
            json=payload,
        )

    # ------------------------------------------------------------------
    # 频道消息
    # ------------------------------------------------------------------
    async def post_channel_message(
        self,
        channel_id: str,
        msg_type: int = _MSG_TYPE_TEXT,
        msg_id: str = "",
        event_id: Optional[str] = None,
        content: Optional[str] = None,
        markdown: Optional[Union[str, Dict[str, Any]]] = None,
        keyboard: Optional[Dict[str, Any]] = None,
        ark: Optional[Dict[str, Any]] = None,
        message_reference: Optional[Dict[str, Any]] = None,
        msg_elements: Optional[List[Dict[str, Any]]] = None,
        image: Optional[str] = None,
    ) -> Dict[str, Any]:
        """发送频道子频道消息（POST /channels/{channel_id}/messages）

        用于回复 AT_MESSAGE_CREATE / DIRECT_MESSAGE_CREATE 等频道消息，
        ``msg_id`` 取事件消息的 ``id`` 即可实现被动回复。
        """
        payload: Dict[str, Any] = {
            "msg_type": msg_type,
            "msg_id": msg_id,
        }
        if event_id is not None:
            payload["event_id"] = event_id
        if content is not None:
            payload["content"] = content
        if markdown is not None:
            payload["markdown"] = _build_markdown(markdown)
        if keyboard is not None:
            payload["keyboard"] = keyboard
        if ark is not None:
            payload["ark"] = ark
        if message_reference is not None:
            payload["message_reference"] = message_reference
        if msg_elements is not None:
            payload["msg_elements"] = msg_elements
        if image is not None:
            payload["image"] = image
        return await self._http.request(
            Route("POST", "/channels/{channel_id}/messages", channel_id=channel_id),
            json=payload,
        )

    # ------------------------------------------------------------------
    # 文件发送
    # ------------------------------------------------------------------
    async def post_group_file(
        self,
        group_openid: str,
        file_type: int,
        url: str,
        srv_send_msg: bool = True,
    ) -> Dict[str, Any]:
        """发送群聊富媒体文件（POST /v2/groups/{group_openid}/files）

        ``url`` 参数自动识别来源：
        - 公网文件地址（``http(s)://``） -> ``url`` 字段
        - base64 数据（``data:image/png;base64,...`` 或纯 base64 字符串） -> ``file_data`` 字段
        """
        payload = {"file_type": file_type, "srv_send_msg": srv_send_msg}
        payload.update(_resolve_file_source(url))
        return await self._http.request(
            Route("POST", "/v2/groups/{group_openid}/files", group_openid=group_openid),
            json=payload,
        )

    async def post_c2c_file(
        self,
        openid: str,
        file_type: int,
        url: str,
        srv_send_msg: bool = True,
    ) -> Dict[str, Any]:
        """发送 C2C 单聊富媒体文件（POST /v2/users/{openid}/files）

        ``url`` 参数自动识别来源：
        - 公网文件地址（``http(s)://``） -> ``url`` 字段
        - base64 数据（``data:image/png;base64,...`` 或纯 base64 字符串） -> ``file_data`` 字段
        """
        payload = {"file_type": file_type, "srv_send_msg": srv_send_msg}
        payload.update(_resolve_file_source(url))
        return await self._http.request(
            Route("POST", "/v2/users/{openid}/files", openid=openid),
            json=payload,
        )

    # ------------------------------------------------------------------
    # 消息撤回（主动 API）
    # ------------------------------------------------------------------
    async def delete_message(self, message_id: str, openid: Optional[str] = None,
                             group_openid: Optional[str] = None) -> Dict[str, Any]:
        """撤回消息（仅沙箱/支持范围内可用，需指定 group_openid 或 openid）"""
        if group_openid:
            return await self._http.request(
                Route("POST", "/v2/groups/{group_openid}/messages/{message_id}/recall",
                      group_openid=group_openid, message_id=message_id),
                json={},
            )
        if openid:
            return await self._http.request(
                Route("POST", "/v2/users/{openid}/messages/{message_id}/recall",
                      openid=openid, message_id=message_id),
                json={},
            )
        raise ValueError("delete_message 需要 group_openid 或 openid")

    # 兼容旧 botpy 命名
    post_group_recall = delete_message
    post_c2c_recall = delete_message
