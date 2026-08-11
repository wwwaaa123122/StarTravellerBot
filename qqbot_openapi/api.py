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


def _build_markdown(
    markdown: Union[str, Dict[str, Any]],
    force_verify_image_resource: Optional[bool] = None,
) -> Dict[str, Any]:
    if isinstance(markdown, str):
        data: Dict[str, Any] = {"content": markdown}
    else:
        data = dict(markdown)
    if force_verify_image_resource is not None:
        data["force_verify_image_resource"] = force_verify_image_resource
    return data


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
        force_verify_image_resource: Optional[bool] = None,
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
            payload["markdown"] = _build_markdown(markdown, force_verify_image_resource)
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
        force_verify_image_resource: Optional[bool] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "openid": openid,
            "msg_type": msg_type,
            "msg_id": msg_id,
        }
        if content is not None:
            payload["content"] = content
        if markdown is not None:
            payload["markdown"] = _build_markdown(markdown, force_verify_image_resource)
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

    # ---- 群禁言管理（2026-08-10 新增）----

    async def get_group_restrict_chat_setting(self, group_openid: str) -> Dict[str, Any]:
        """查询群禁言状态，包含全员禁言模式与成员级禁言列表。机器人需拥有群管理员身份。"""
        return await self._http.request(
            Route("GET", "/v2/groups/{group_openid}/restrict_chat_setting", group_openid=group_openid),
        )

    async def set_group_restrict_chat_setting(
        self,
        group_openid: str,
        members: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """设置群成员级禁言。

        members 每项: op (add/update/del), member_openid, mute_expire_at（RFC3339，op=del 时可传空串）。
        单次设置不能超过 10 个成员。
        """
        return await self._http.request(
            Route("POST", "/v2/groups/{group_openid}/restrict_chat_setting", group_openid=group_openid),
            json={"members": members},
        )

    # ---- 入群申请审批（2026-08-10 新增）----

    async def get_group_join_request_list(
        self,
        group_openid: str,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """拉取入群申请列表，支持分页。机器人需拥有群管理员身份。"""
        payload: Dict[str, Any] = {}
        if cursor is not None:
            payload["cursor"] = cursor
        if limit is not None:
            payload["limit"] = limit
        return await self._http.request(
            Route("GET", "/v2/groups/{group_openid}/join_request_list", group_openid=group_openid),
            params=payload,
        )

    async def approval_join_request(
        self,
        group_openid: str,
        member_openid: str,
        op: str,
        join_request_id: Optional[str] = None,
        reject_reason: Optional[str] = None,
        add_to_member_blacklist: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """审批入群申请。op: approve 通过，decline 拒绝。机器人需拥有群管理员身份。"""
        payload: Dict[str, Any] = {"op": op}
        if join_request_id is not None:
            payload["join_request_id"] = join_request_id
        if reject_reason is not None:
            payload["reject_reason"] = reject_reason
        if add_to_member_blacklist is not None:
            payload["add_to_member_blacklist"] = add_to_member_blacklist
        return await self._http.request(
            Route(
                "POST",
                "/v2/groups/{group_openid}/approval_join_request/{member_openid}",
                group_openid=group_openid,
                member_openid=member_openid,
            ),
            json=payload,
        )

    # ---- 入群自动审批策略（2026-08-10 新增）----

    async def get_join_approval_strategies(
        self,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """查询当前生效中的入群自动审批策略列表，按创建时间倒序，支持分页。"""
        payload: Dict[str, Any] = {}
        if cursor is not None:
            payload["cursor"] = cursor
        if limit is not None:
            payload["limit"] = limit
        return await self._http.request(
            Route("GET", "/v2/groups/join_approval_strategy"),
            params=payload,
        )

    async def create_join_approval_strategy(
        self,
        group_openids: Optional[List[str]] = None,
        group_ids: Optional[List[int]] = None,
        is_enable: Optional[str] = None,
        expire_at: Optional[str] = None,
        remark: Optional[str] = None,
    ) -> Dict[str, Any]:
        """创建入群自动审批策略。group_openids 与 group_ids 二选一必填，一个机器人最多 20 个策略。"""
        payload: Dict[str, Any] = {}
        if group_openids is not None:
            payload["group_openids"] = group_openids
        if group_ids is not None:
            payload["group_ids"] = group_ids
        if is_enable is not None:
            payload["is_enable"] = is_enable
        if expire_at is not None:
            payload["expire_at"] = expire_at
        if remark is not None:
            payload["remark"] = remark
        return await self._http.request(
            Route("POST", "/v2/groups/join_approval_strategy"),
            json=payload,
        )

    async def delete_join_approval_strategy(self, strategy_id: str) -> Dict[str, Any]:
        """删除指定的入群自动审批策略。"""
        return await self._http.request(
            Route("DELETE", "/v2/groups/join_approval_strategy/{strategy_id}", strategy_id=strategy_id),
        )

    async def update_join_approval_strategy(
        self,
        strategy_id: str,
        is_enable: Optional[str] = None,
        expire_at: Optional[str] = None,
        group_action: Optional[Dict[str, Any]] = None,
        remark: Optional[str] = None,
    ) -> Dict[str, Any]:
        """修改入群自动审批策略的生效状态、失效时间或增删关联群。

        group_action 形如 {"op": "add"|"del", "group_openids": [...]} 或 {"op": ..., "group_ids": [...]}。
        """
        payload: Dict[str, Any] = {}
        if is_enable is not None:
            payload["is_enable"] = is_enable
        if expire_at is not None:
            payload["expire_at"] = expire_at
        if group_action is not None:
            payload["group_action"] = group_action
        if remark is not None:
            payload["remark"] = remark
        return await self._http.request(
            Route("PATCH", "/v2/groups/join_approval_strategy/{strategy_id}", strategy_id=strategy_id),
            json=payload,
        )

    async def execute_join_approval_strategy(self, strategy_id: str) -> Dict[str, Any]:
        """对策略关联的全部群发起全量扫描，命中白名单号码的入群申请自动审批通过。异步执行，约 10 分钟完成。"""
        return await self._http.request(
            Route(
                "POST",
                "/v2/groups/join_approval_strategy/{strategy_id}/execute",
                strategy_id=strategy_id,
            ),
            json={},
        )

    async def update_join_approval_strategy_whitelist(
        self,
        strategy_id: str,
        op: str,
        whitelist_users: List[str],
    ) -> Dict[str, Any]:
        """修改入群自动审批策略的白名单号码。op: add 新增号码，del 删除号码；单次最多 10000 个，号码上限 10W。"""
        payload = {"op": op, "whitelist_users": whitelist_users}
        return await self._http.request(
            Route(
                "POST",
                "/v2/groups/join_approval_strategy/{strategy_id}/whitelist_users",
                strategy_id=strategy_id,
            ),
            json=payload,
        )

    post_group_recall = delete_message
    post_c2c_recall = delete_message
