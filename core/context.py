# -*- coding: utf-8 -*-

from typing import Any, Dict, Optional

from core.permissions import is_root


class PluginContext:

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

        for key, value in compat.items():
            if not hasattr(self, key):
                setattr(self, key, value)

    def is_root(self, user_id: Optional[str] = None) -> bool:
        return is_root(user_id or self.user_id, self.config)

    @property
    def permission(self):
        return self

    async def reply(self, content: Optional[str] = None, markdown: Optional[dict] = None):
        await self.client._reply(self.message, content=content, markdown=markdown)

    async def send(self, **kwargs):
        await self.actions.send(**kwargs)

    async def send_file(self, **kwargs):
        await self.actions.send_file(**kwargs)

    async def send_local_file(self, file_path: str, file_type: int = 1):
        await self.actions.send_local_file(file_path, file_type)
