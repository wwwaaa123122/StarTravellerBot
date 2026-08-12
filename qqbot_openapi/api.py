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
        event_id: str | None = None,
        media: dict[str, Any] | None = None,
        is_wakeup: bool | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "group_openid": group_openid,
            "msg_type": msg_type,
            "msg_id": msg_id,
        }
        if msg_seq is not None:
            payload["msg_seq"] = msg_seq
        if event_id is not None:
            payload["event_id"] = event_id
        if is_wakeup is not None:
            payload["is_wakeup"] = is_wakeup
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
        if media is not None:
            payload["media"] = media
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
        msg_seq: int | None = None,
        event_id: str | None = None,
        media: dict[str, Any] | None = None,
        is_wakeup: bool | None = None,
        input_notify: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "openid": openid,
            "msg_type": msg_type,
            "msg_id": msg_id,
        }
        if msg_seq is not None:
            payload["msg_seq"] = msg_seq
        if event_id is not None:
            payload["event_id"] = event_id
        if is_wakeup is not None:
            payload["is_wakeup"] = is_wakeup
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
        if media is not None:
            payload["media"] = media
        if input_notify is not None:
            payload["input_notify"] = input_notify
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
        url: str = "",
        srv_send_msg: bool = True,
        file_name: str | None = None,
        upload_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"file_type": file_type, "srv_send_msg": srv_send_msg}
        if upload_id is not None:
            payload["upload_id"] = upload_id
        else:
            payload.update(_resolve_file_source(url))
            if not (payload.get("url") or payload.get("file_data")):
                raise ValueError("post_group_file 需要 url、file_data 或 upload_id")
        if file_name is not None:
            payload["file_name"] = file_name
        return await self._http.request(
            Route("POST", "/v2/groups/{group_openid}/files", group_openid=group_openid),
            json=payload,
        )

    async def post_c2c_file(
        self,
        openid: str,
        file_type: int,
        url: str = "",
        srv_send_msg: bool = True,
        file_name: str | None = None,
        upload_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"file_type": file_type, "srv_send_msg": srv_send_msg}
        if upload_id is not None:
            payload["upload_id"] = upload_id
        else:
            payload.update(_resolve_file_source(url))
            if not (payload.get("url") or payload.get("file_data")):
                raise ValueError("post_c2c_file 需要 url、file_data 或 upload_id")
        if file_name is not None:
            payload["file_name"] = file_name
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

    # ---- 流式消息（单聊，官方支持 AI 流式回复）----

    async def post_stream_message(
        self,
        user_openid: str,
        input_mode: str | None = None,
        input_state: int | None = None,
        index: int | None = None,
        content_type: str | None = None,
        content_raw: str | None = None,
        event_id: str | None = None,
        msg_id: str | None = None,
        stream_msg_id: str | None = None,
        msg_seq: int | None = None,
        is_wakeup: bool | None = None,
    ) -> dict[str, Any]:
        """流式发送单聊消息，每个分片使用相同 stream_msg_id，index 从 0 递增。

        - 首片不传 stream_msg_id，由服务端在响应 id 中返回，后续分片需携带。
        - input_mode: append（默认，ContentRaw 拼接）或 replace（全量正文）。
        - input_state: 1=生成中，10=生成结束。
        - content_type: text 或 markdown。
        - 被动回复用 msg_id 或 event_id（二选一），is_wakeup 声明互动召回消息。
        """
        payload: dict[str, Any] = {}
        if input_mode is not None:
            payload["input_mode"] = input_mode
        if input_state is not None:
            payload["input_state"] = input_state
        if index is not None:
            payload["index"] = index
        if content_type is not None:
            payload["content_type"] = content_type
        if content_raw is not None:
            payload["content_raw"] = content_raw
        if event_id is not None:
            payload["event_id"] = event_id
        if msg_id is not None:
            payload["msg_id"] = msg_id
        if stream_msg_id is not None:
            payload["stream_msg_id"] = stream_msg_id
        if msg_seq is not None:
            payload["msg_seq"] = msg_seq
        if is_wakeup is not None:
            payload["is_wakeup"] = is_wakeup
        return await self._http.request(
            Route("POST", "/v2/users/{user_openid}/stream_messages", user_openid=user_openid),
            json=payload,
        )

    # ---- 富媒体分片上传（upload_prepare -> 逐片 PUT 预签名 URL -> upload_part_finish -> files 合并）----

    async def post_c2c_upload_prepare(
        self,
        openid: str,
        file_type: int,
        file_size: int | str,
        file_name: str,
        md5: str,
        sha1: str,
        md5_10m: str,
    ) -> dict[str, Any]:
        """单聊大文件分片上传准备工作，返回 upload_id、block_size、parts 预签名 URL 与 upload_config。

        file_type: 1=图片, 2=视频, 3=语音, 4=文件。随后逐片 PUT 到 parts[].presigned_url，
        每片成功后调用 post_c2c_upload_part_finish，全部分片完成后调用 post_c2c_file 合并。
        """
        payload = {
            "file_type": file_type,
            "file_size": str(file_size),
            "file_name": file_name,
            "md5": md5,
            "sha1": sha1,
            "md5_10m": md5_10m,
        }
        return await self._http.request(
            Route("POST", "/v2/users/{openid}/upload_prepare", openid=openid),
            json=payload,
        )

    async def post_group_upload_prepare(
        self,
        group_openid: str,
        file_type: int,
        file_size: int | str,
        file_name: str,
        md5: str,
        sha1: str,
        md5_10m: str,
    ) -> dict[str, Any]:
        """群聊大文件分片上传准备工作，参数与返回同 post_c2c_upload_prepare。"""
        payload = {
            "file_type": file_type,
            "file_size": str(file_size),
            "file_name": file_name,
            "md5": md5,
            "sha1": sha1,
            "md5_10m": md5_10m,
        }
        return await self._http.request(
            Route("POST", "/v2/groups/{group_openid}/upload_prepare", group_openid=group_openid),
            json=payload,
        )

    async def post_c2c_upload_part_finish(
        self,
        openid: str,
        upload_id: str,
        part_index: int,
        block_size: int | str,
        md5: str,
    ) -> dict[str, Any]:
        """通知服务端单聊某个分片已上传完成（每片 PUT 成功后调用）。"""
        payload = {
            "upload_id": upload_id,
            "part_index": part_index,
            "block_size": str(block_size),
            "md5": md5,
        }
        return await self._http.request(
            Route("POST", "/v2/users/{openid}/upload_part_finish", openid=openid),
            json=payload,
        )

    async def post_group_upload_part_finish(
        self,
        group_openid: str,
        upload_id: str,
        part_index: int,
        block_size: int | str,
        md5: str,
    ) -> dict[str, Any]:
        """通知服务端群聊某个分片已上传完成（每片 PUT 成功后调用）。"""
        payload = {
            "upload_id": upload_id,
            "part_index": part_index,
            "block_size": str(block_size),
            "md5": md5,
        }
        return await self._http.request(
            Route("POST", "/v2/groups/{group_openid}/upload_part_finish", group_openid=group_openid),
            json=payload,
        )

    # ---- 群信息查询（需白名单权限）----

    async def get_group_info(self, group_openid: str) -> dict[str, Any]:
        """获取群基本信息（群名/简介/分类/标签/成员数），需白名单权限。"""
        return await self._http.request(
            Route("GET", "/v2/groups/{group_openid}/info", group_openid=group_openid),
        )

    async def get_group_bot_state(self, group_openid: str) -> dict[str, Any]:
        """获取机器人在群内的状态（openid/入群时间/是否接收主动推送/消息接收设置/群成员角色）。"""
        return await self._http.request(
            Route("GET", "/v2/groups/{group_openid}/bot_state", group_openid=group_openid),
        )

    post_group_recall = delete_message
    post_c2c_recall = delete_message
