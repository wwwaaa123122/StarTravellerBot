# -*- coding: utf-8 -*-

from typing import Any, Dict, List, Optional, Union

from . import logging
from .http import HTTPClient, Route

_log = logging.get_logger(__name__)

_MSG_TYPE_TEXT = 0
_MSG_TYPE_MARKDOWN = 2


def _resolve_file_source(value: str) -> Dict[str, str]:
    value = (value or "").strip()
    if value.startswith(("http://", "https://")):
        return {"url": value}
    if value.startswith("data:") and ";base64," in value:
        value = value.split(";base64,", 1)[1]
    return {"file_data": value}


def _build_markdown(markdown: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    if isinstance(markdown, str):
        return {"content": markdown}
    return markdown


class API:

    def __init__(self, http_client: HTTPClient):
        self._http = http_client

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

    async def post_group_file(
        self,
        group_openid: str,
        file_type: int,
        url: str,
        srv_send_msg: bool = True,
    ) -> Dict[str, Any]:
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
        payload = {"file_type": file_type, "srv_send_msg": srv_send_msg}
        payload.update(_resolve_file_source(url))
        return await self._http.request(
            Route("POST", "/v2/users/{openid}/files", openid=openid),
            json=payload,
        )

    async def delete_message(self, message_id: str, openid: Optional[str] = None,
                             group_openid: Optional[str] = None) -> Dict[str, Any]:
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

    post_group_recall = delete_message
    post_c2c_recall = delete_message
