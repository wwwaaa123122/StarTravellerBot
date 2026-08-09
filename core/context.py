# -*- coding: utf-8 -*-
"""插件上下文（新插件 API）：on_message(ctx) 的唯一入口。

ctx 暴露全部能力：event/actions/config/http/权限/回复方法；
旧版 kwargs 字段同时挂到 ctx 顶层与 ctx.kwargs，便于渐进迁移。
"""

from typing import Any, Dict, Optional

from core.permissions import is_root


class PluginContext:
    """插件执行上下文；reply/send 为推荐的回复方式。"""

    def __init__(self, client, message, order: str, event, actions, compat: Dict[str, Any]):
        self.client = client
        self.message = message
        self.order = order
        self.event = event
        self.actions = actions
        self.config = client.config
        self.bot_name = client.bot_name
        self.reminder = client.reminder
        self.user_id = str(getattr(event, "user_id", ""))
        self.group_id = getattr(event, "group_id", None)
        self.nickname = getattr(event, "nickname", "") or ""
        self.http = getattr(client, "http_client", None)
        self.kwargs = compat

        # 旧版 kwargs 字段透传到 ctx 顶层
        for key, value in compat.items():
            if not hasattr(self, key):
                setattr(self, key, value)

    def is_root(self, user_id: Optional[str] = None) -> bool:
        """用户是否为管理员（默认当前用户）。"""
        return is_root(user_id or self.user_id, self.config)

    @property
    def permission(self):
        return self

    async def reply(self, content: Optional[str] = None, markdown: Optional[dict] = None):
        """回复当前消息（自动识别群聊/单聊，Markdown 自动探测）。"""
        await self.client._reply(self.message, content=content, markdown=markdown)

    async def send(self, **kwargs):
        """发送消息（content/message/markdown），与旧版 actions.send 一致。"""
        await self.actions.send(**kwargs)

    async def send_file(self, **kwargs):
        """发送文件（网络 URL / BytesIO / 本地路径），与旧版 actions.send_file 一致。"""
        await self.actions.send_file(**kwargs)

    async def send_local_file(self, file_path: str, file_type: int = 1):
        await self.actions.send_local_file(file_path, file_type)
