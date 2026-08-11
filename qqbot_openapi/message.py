# -*- coding: utf-8 -*-

from typing import Any, List, Optional, Union


def _wrap(value: Any) -> Any:
    if isinstance(value, dict):
        return Model(value)
    if isinstance(value, list):
        return [_wrap(item) for item in value]
    return value


def _unwrap(value: Any) -> Any:
    if isinstance(value, Model):
        return value.to_dict()
    if isinstance(value, list):
        return [_unwrap(item) for item in value]
    return value


class Model:

    __slots__ = ("_data", "_api")

    def __init__(self, data: Optional[dict] = None, api: Any = None):
        object.__setattr__(self, "_data", data or {})
        object.__setattr__(self, "_api", api)

    def _set_api(self, api: Any) -> None:
        object.__setattr__(self, "_api", api)

    def __getattr__(self, name: str) -> Any:
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
    pass


class GroupMessage(Model):
    pass


class DirectMessage(Model):
    pass


class Group(Model):
    pass


class GroupJoinRequest(Model):
    pass


class FriendUser(Model):
    pass


class Ready(Model):
    pass


class Guild(Model):
    pass


class Channel(Model):
    pass


class GuildMember(Model):
    pass


class Reaction(Model):
    pass


class Interaction(Model):
    pass


class MessageAudit(Model):
    pass


class Thread(Model):
    pass


class Post(Model):
    pass


class Reply(Model):
    pass


class AuditResult(Model):
    pass


class Audio(Model):
    pass


User = Model
Author = Model
Member = GuildMember
Embed = Model
Attachment = Model
MessageReference = Model
