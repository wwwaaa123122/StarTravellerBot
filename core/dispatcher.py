# -*- coding: utf-8 -*-
"""消息分发器：按场景配置统一处理单聊/群聊/频道消息流程。"""

import re
import traceback
from dataclasses import dataclass, field
from typing import Callable, Optional, Set


@dataclass
class Scene:
    """场景配置：描述一种消息来源的处理规则。"""
    name: str
    log_prefix: str
    user_id_attr: str
    user_name: Optional[Callable] = None
    group_attr: str = "group_openid"
    strip_mention: bool = False
    strip_mentions_regex: bool = False
    use_plugins: bool = False
    skip_plugins: Set[str] = field(default_factory=set)
    reply_direct: bool = False
    use_markdown_ai: bool = False
    allow_ai: bool = False
    min_content_len: int = 1
    handle_status: bool = False
    handle_logout: bool = False
    empty_action: str = "ignore"  # greet | group_hint | help | ignore
    reminder_check_raw: bool = False  # 用剥离 @提及 前的原文判断 reminder 前缀（群全量场景）
    reply_on_reminder_match: bool = False  # True=前缀命中才提示未找到；False=前缀未命中才提示


class Dispatcher:
    """消息分发：昵称记录 -> 统计 -> 内置指令 -> 插件 -> AI。"""

    def __init__(self, client):
        self.client = client

    async def route(self, message, scene: Scene):
        client = self.client
        try:
            content = (message.content or "").strip()
            raw_content = content
            author = getattr(message, "author", None)
            user_id = str(getattr(author, scene.user_id_attr, "") or "")
            group_id = getattr(message, scene.group_attr, None)

            if scene.strip_mention:
                content = client._strip_mention(content)
            if scene.strip_mentions_regex:
                content = re.sub(r'<@!?\w+>', '', content).strip()

            nickname = client._try_get_nickname(message)
            client.stats.record_nickname(user_id, nickname)
            user_label = f"{nickname}({user_id})" if nickname else user_id
            if group_id:
                client.logger.info(f"[{scene.log_prefix}] 群 {group_id} 用户 {user_label}: {content}")
            else:
                client.logger.info(f"[{scene.log_prefix}] 用户 {user_label}: {content}")

            client.stats.record_message()

            if not content:
                await self._handle_empty(message, scene)
                return

            order = content
            if scene.use_plugins and (order.startswith("+") or order.startswith("/")):
                order = order[1:].strip()

            if order.lower() == "ping":
                await client._handle_ping(message)
                return

            if scene.use_plugins:
                help_match = order == "帮助"
                status_match = order == "状态"
            else:
                help_match = order in ("帮助", f"{client.reminder}帮助")
                status_match = order in ("状态", f"{client.reminder}状态")

            if help_match:
                await client._handle_help_command(message)
                return

            if scene.handle_status and status_match:
                await client._handle_status_command(message)
                return

            if scene.use_plugins:
                if await client._handle_roleplay_command(message, order):
                    return
                if await client.plugin_manager.try_plugins(message, order, skip_plugins=scene.skip_plugins):
                    return
                reminder_content = raw_content if scene.reminder_check_raw else content
                if (reminder_content.startswith(client.reminder)) == scene.reply_on_reminder_match:
                    await client._send_message(message, f"未找到匹配的插件命令，发送 @机器人 /帮助 查看可用指令")
                return

            # ---- AI 场景 ----
            if scene.handle_logout and order in ("注销", f"{client.reminder}注销"):
                client.context.user_lists.pop(user_id, None)
                await client._send_message(message, "已清除你的对话上下文记忆")
                client.logger.info(f"[{scene.log_prefix}] 用户 {user_label} 已清除上下文")
                return

            if await client._handle_roleplay_command(message, order):
                return

            if not client.allow_ai:
                await self._ai_unavailable(message)
                return

            if order.startswith(client.reminder):
                ai_order = order[len(client.reminder):].strip()
                if len(ai_order) >= 2:
                    await client._handle_ai_chat(message, ai_order, user_id, self._user_name(message, scene), use_markdown=scene.use_markdown_ai)
                    return

            if len(order) >= scene.min_content_len:
                await client._handle_ai_chat(message, order, user_id, self._user_name(message, scene), use_markdown=scene.use_markdown_ai)

        except Exception as e:
            client.logger.error(f"处理{scene.name}错误: {traceback.format_exc()}")
            await self._error_reply(message, scene, e)

    @staticmethod
    def _user_name(message, scene: Scene) -> str:
        if scene.user_name:
            return scene.user_name(message)
        return "用户"

    async def _handle_empty(self, message, scene: Scene):
        client = self.client
        if scene.empty_action == "greet":
            text = f"你好呀~ 我是{client.bot_name}，有什么可以帮你的吗？"
            if scene.reply_direct:
                await message.reply(content=text)
            else:
                await client._send_message(message, text)
        elif scene.empty_action == "group_hint":
            await client._send_message(message, f"发送 @机器人 /帮助 查看可用指令")
        elif scene.empty_action == "help":
            help_text = client.plugin_manager.get_help_text(client.bot_name, client.version_name)
            sent = await client._send_help_image(message, help_text)
            if not sent:
                await message.reply(content=help_text)

    async def _ai_unavailable(self, message):
        client = self.client
        if hasattr(message, 'reply'):
            await message.reply(content=f"未找到相关指令")
        else:
            await client._send_message(message, f"未找到相关指令")

    async def _error_reply(self, message, scene: Scene, exc: Exception):
        client = self.client
        text = f"{client.bot_name} 发生错误了，请稍后再试\n\n错误信息: {exc}\n联系管理员: https://xc-lr.cn/about"
        try:
            if scene.reply_direct:
                await message.reply(content=text)
            else:
                await client._send_message(message, text)
        except Exception:
            pass


# 单聊 (C2C_MESSAGE_CREATE)
SCENE_C2C = Scene(
    name="单聊",
    log_prefix="单聊",
    user_id_attr="user_openid",
    allow_ai=True,
    min_content_len=1,
    handle_status=True,
    handle_logout=True,
    empty_action="greet",
)

# 群聊@机器人 (GROUP_AT_MESSAGE_CREATE)
SCENE_GROUP_AT = Scene(
    name="群聊",
    log_prefix="群聊",
    user_id_attr="member_openid",
    strip_mention=True,
    use_plugins=True,
    handle_status=True,
    empty_action="group_hint",
)

# 群聊全量 (GROUP_MESSAGE_CREATE)
SCENE_GROUP = Scene(
    name="群聊全量",
    log_prefix="群聊全量",
    user_id_attr="member_openid",
    strip_mentions_regex=True,
    use_plugins=True,
    skip_plugins={"affection"},
    handle_status=True,
    empty_action="ignore",
    reminder_check_raw=True,
    reply_on_reminder_match=True,
)

# 频道私信 (DIRECT_MESSAGE_CREATE)
SCENE_DIRECT = Scene(
    name="频道私信",
    log_prefix="频道私信",
    user_id_attr="id",
    user_name=lambda m: getattr(m.author, "username", "用户"),
    reply_direct=True,
    use_markdown_ai=True,
    allow_ai=True,
    min_content_len=2,
    empty_action="greet",
)

# 频道@机器人 (AT_MESSAGE_CREATE)
SCENE_AT = Scene(
    name="频道",
    log_prefix="频道",
    user_id_attr="id",
    user_name=lambda m: getattr(m.author, "username", "用户"),
    strip_mention=True,
    reply_direct=True,
    use_markdown_ai=True,
    allow_ai=True,
    min_content_len=2,
    handle_status=True,
    empty_action="help",
)
