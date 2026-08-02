# -*- coding: utf-8 -*-
"""消息/事件数据模型

与官方文档事件体字段一一对应。模型为"字典兜底"式：顶层字段直接作为属性
访问，嵌套 dict 自动包装为 :class:`Model`，因此可以透明访问任意官方字段
（如 ``message.author.user_openid``、``message.group_openid``）。

字段访问语义：
- 已知字段（事件数据中存在的 key）缺失时返回 ``None``；
- 未知字段（拼写错误或未声明）抛 ``AttributeError``，避免静默吞掉 typo；
- 需要宽松取值时请显式使用 :meth:`Model.get`。
"""

from typing import Any, List, Optional, Union


def _wrap(value: Any) -> Any:
    """递归包装 dict 与 list，使嵌套字段也支持属性访问"""
    if isinstance(value, dict):
        return Model(value)
    if isinstance(value, list):
        return [_wrap(item) for item in value]
    return value


def _unwrap(value: Any) -> Any:
    """递归还原为普通 dict/list"""
    if isinstance(value, Model):
        return value.to_dict()
    if isinstance(value, list):
        return [_unwrap(item) for item in value]
    return value


class Model:
    """通用数据模型：由事件/响应字典构造，字段即属性"""

    __slots__ = ("_data", "_api")

    def __init__(self, data: Optional[dict] = None, api: Any = None):
        object.__setattr__(self, "_data", data or {})
        object.__setattr__(self, "_api", api)

    def _set_api(self, api: Any) -> None:
        """注入 API 客户端引用，使消息对象具备 reply() 能力"""
        object.__setattr__(self, "_api", api)

    def __getattr__(self, name: str) -> Any:
        # 未知字段（拼写错误等）抛 AttributeError 及早暴露；已知字段缺失返回 None。
        # 宽松取值请用 self.get(name, default)。
        if name not in self._data:
            raise AttributeError(
                f"{type(self).__name__!r} object has no field {name!r}"
            )
        return _wrap(self._data[name])

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_api":
            object.__setattr__(self, "_api", value)
        else:
            self._data[name] = value

    def get(self, name: str, default: Any = None) -> Any:
        return self._data.get(name, default)

    def to_dict(self) -> dict:
        return {key: _unwrap(value) for key, value in self._data.items()}

    def __contains__(self, name: str) -> bool:
        return name in self._data

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self._data!r}>"

    async def reply(
        self,
        content: Optional[str] = None,
        markdown: Optional[Union[str, dict]] = None,
        **kwargs: Any,
    ) -> dict:
        """回复当前消息，按消息场景自动分发：
        群聊（group_openid）→ 群聊 API；频道/私信（channel_id）→ 频道 API；
        C2C（author.user_openid）→ 单聊 API。markdown 非空时 msg_type 置为 2。
        """
        api = self._api
        if api is None:
            raise RuntimeError("消息对象未绑定 API 引用，无法调用 reply()")
        msg_type = 2 if markdown is not None else 0
        msg_id = self._data.get("id") or ""
        group_openid = self._data.get("group_openid")
        channel_id = self._data.get("channel_id")
        author = self._data.get("author") or {}
        if isinstance(author, dict):
            openid = author.get("user_openid")
        else:
            openid = getattr(author, "user_openid", None)
        if group_openid:
            return await api.post_group_message(
                group_openid=group_openid,
                msg_type=msg_type,
                msg_id=msg_id,
                content=content,
                markdown=markdown,
                **kwargs,
            )
        if channel_id:
            return await api.post_channel_message(
                channel_id=channel_id,
                msg_type=msg_type,
                msg_id=msg_id,
                content=content,
                markdown=markdown,
                **kwargs,
            )
        if openid:
            return await api.post_c2c_message(
                openid=openid,
                msg_type=msg_type,
                msg_id=msg_id,
                content=content,
                markdown=markdown,
                **kwargs,
            )
        raise RuntimeError(
            "无法确定消息回复目标（缺少 group_openid / channel_id / user_openid）"
        )


class Message(Model):
    """频道消息（AT_MESSAGE_CREATE / 公域频道消息）"""


class GroupMessage(Model):
    """群聊 / C2C 单聊消息

    群聊消息带 ``group_openid``；C2C 消息带 ``author.user_openid``。
    事件体字段：id、author、content、timestamp、group_openid、message_type、
    message_scene、attachments、mentions、ark_data、msg_elements 等。
    """


class DirectMessage(Model):
    """频道私信（DIRECT_MESSAGE_CREATE）"""


class Group(Model):
    """群事件载体（GROUP_ADD_ROBOT / GROUP_DEL_ROBOT / GROUP_MSG_REJECT /
    GROUP_MSG_RECEIVE），字段：group_openid、op_member_openid、timestamp、scene"""


class FriendUser(Model):
    """好友事件载体（FRIEND_ADD / FRIEND_DEL），字段：openid、timestamp、
    scene、scene_param、author"""


class Ready(Model):
    """READY 事件：version、session_id、user、shard"""


# 类型别名，兼容 botpy 风格导入
User = Model
Author = Model
Member = Model
Embed = Model
Attachment = Model
MessageReference = Model
