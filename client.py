# -*- coding: utf-8 -*-
"""
QQ 开放平台机器人客户端
实现 main.py 的主要功能，适配 QQ 开放平台 API

事件类型:
- C2C_MESSAGE_CREATE: 单聊消息
- GROUP_AT_MESSAGE_CREATE: 群聊@机器人消息
- GROUP_MESSAGE_CREATE: 群聊消息(非@,与 AT 格式相同)
- DIRECT_MESSAGE_CREATE: 频道私信消息
- AT_MESSAGE_CREATE: 频道@机器人消息
- MESSAGE_CREATE: 频道全量消息(私域)
"""

import os
import re
import sys
import time
import json
import asyncio
import traceback
import inspect
from typing import Dict, Any, Optional

import httpx
import botpy
from botpy import logging
from botpy.message import Message, DirectMessage

# ==================== botpy 补丁 ====================
# QQ 开放平台会发送 GROUP_MESSAGE_CREATE 事件，但当前 botpy 版本缺少对应的解析器。
# 这里通过 monkey-patch 添加缺失的处理方法。

from botpy.connection import ConnectionState
from botpy.message import GroupMessage as _GroupMessage


def _parse_group_message_create(self, payload):
    """解析 GROUP_MESSAGE_CREATE 事件"""
    _message = _GroupMessage(
        self.api,
        payload.get("id", None),
        payload.get("d", {}),
    )
    self._dispatch("group_message_create", _message)


if not hasattr(ConnectionState, "parse_group_message_create"):
    ConnectionState.parse_group_message_create = _parse_group_message_create

# ==================== aiohttp 兼容补丁 ====================
# aiohttp 3.14+ 的 FormData 移除了 _is_processed 属性，
# botpy._FormData._gen_form_data 覆写与之不兼容。
# 父类的 _gen_form_data 已足够，直接替换掉 botpy 的覆写。
from botpy.http import _FormData as _BotpyFormData
_BotpyFormData._gen_form_data = _BotpyFormData.__bases__[0]._gen_form_data
# ==================== 补丁结束 ====================

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from Tools.core import BotContext, VERSION_NAME
from Tools.rag_memory import RAGMemory
from ai.role_manager import RoleManager
from ai.chat import AIChat


class XCLRClient(botpy.Client):
    """
    星辰旅人 QQ 开放平台机器人客户端

    支持的场景:
    1. QQ 单聊 (C2C_MESSAGE_CREATE)
    2. QQ 群聊@机器人 (GROUP_AT_MESSAGE_CREATE)
    3. 频道私信 (DIRECT_MESSAGE_CREATE)
    4. 频道@机器人 (AT_MESSAGE_CREATE)
    """

    def __init__(self, config: Dict[str, Any], **kwargs):
        """
        初始化机器人客户端

        Args:
            config: 配置字典
        """
        # 订阅事件
        intents = botpy.Intents(
            public_guild_messages=True,  # 频道公域消息 (AT_MESSAGE_CREATE)
            public_messages=True,        # 群/C2C公域消息 (GROUP_AT_MESSAGE_CREATE, C2C_MESSAGE_CREATE)
            direct_message=True,         # 频道私信
            guilds=True,                 # 频道事件
            guild_members=True,          # 频道成员事件
        )
        super().__init__(intents=intents, **kwargs)

        self.config = config
        others = config.get("Others", {})
        self.bot_name = others.get("bot_name", "星辰旅人")
        self.bot_name_en = others.get("bot_name_en", "XCLR")
        self.reminder = others.get("reminder", "#")
        self.root_users = others.get("ROOT_User", [])
        self.version_name = VERSION_NAME

        # 初始化运行上下文
        self.context = BotContext()
        self.context.EnableNetwork = others.get("default_mode", "Ds")

        # AI 开关 (通过 config.json 中 Others.allow_ai 控制)
        self.allow_ai = others.get("allow_ai", True)

        # 插件系统
        self._plugins = []
        self._plugins_help = {}
        self._plugins_bg_tasks = []

        # RAG 记忆
        self.rag = RAGMemory(os.path.join(PROJECT_ROOT, "data"))

        # 日志
        self.logger = logging.get_logger()

        # 角色管理器
        self.role_manager = RoleManager()

        # AI 对话
        self.ai_chat = AIChat(
            config=config,
            context=self.context,
            rag=self.rag,
            http_client=self.http_client,
            logger=self.logger,
            bot_name=self.bot_name,
            bot_username=self.bot_name_en,
            role_manager=self.role_manager,
        )

    @property
    def http_client(self) -> httpx.AsyncClient:
        if not hasattr(self, '_http_client_instance') or self._http_client_instance.is_closed:
            self._http_client_instance = httpx.AsyncClient(timeout=60.0)
        return self._http_client_instance

    async def close(self):
        if hasattr(self, '_http_client_instance') and not self._http_client_instance.is_closed:
            await self._http_client_instance.aclose()
        await super().close()

    async def on_ready(self):
        """机器人就绪事件"""
        self.logger.info(f"{'='*50}")
        self.logger.info(f"{self.bot_name} 已上线!")
        self.logger.info(f"Version: {self.version_name}")
        self.logger.info(f"AI 模型: {self.context.EnableNetwork}")
        self.logger.info(f"AI 对话: {'开启' if self.allow_ai else '关闭'}")
        self.logger.info(f"{'='*50}")

        # 加载插件
        self._load_plugins()

        # 启动插件后台任务
        await self._start_plugin_background_tasks()

    @staticmethod
    def _is_plugin_file(filename: str) -> bool:
        return filename.endswith(".py") and not filename.startswith(("__", "d_"))

    def _load_plugin_module(self, plugin_dir: str, filename: str):
        import importlib.util

        plugin_name = filename[:-3]
        plugin_path = os.path.join(plugin_dir, filename)
        spec = importlib.util.spec_from_file_location(f"plugins.{plugin_name}", plugin_path)
        if not spec or not spec.loader:
            raise ImportError(f"无法创建插件加载规范: {filename}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return plugin_name, module

    def _register_plugin(self, plugin_name: str, module) -> bool:
        keyword = getattr(module, 'TRIGGHT_KEYWORD', None)
        help_msg = getattr(module, 'HELP_MESSAGE', '')
        on_message = getattr(module, 'on_message', None)

        if not keyword or not callable(on_message):
            return False

        keyword = keyword.strip()
        self._plugins.append({
            'name': plugin_name,
            'keyword': keyword,
            'help': help_msg,
            'module': module,
            'on_message': on_message,
            'is_any': keyword == 'Any',
        })
        self._plugins_help[plugin_name] = help_msg
        self.logger.info(f"加载插件: {plugin_name} ({keyword})")
        return True

    def _register_plugin_background_task(self, plugin_name: str, module):
        bg_tasks = getattr(module, 'background_tasks', None)
        if callable(bg_tasks):
            self._plugins_bg_tasks.append({
                'name': plugin_name,
                'task': bg_tasks,
            })
            self.logger.info(f"插件 {plugin_name} 注册后台任务")

    def _load_plugins(self):
        """加载插件"""
        plugin_dir = os.path.join(PROJECT_ROOT, "plugins")
        self._plugins.clear()
        self._plugins_help.clear()
        self._plugins_bg_tasks.clear()

        if not os.path.exists(plugin_dir):
            self.logger.warning(f"插件目录不存在: {plugin_dir}")
            return

        for filename in sorted(os.listdir(plugin_dir)):
            if not self._is_plugin_file(filename):
                continue

            plugin_name = filename[:-3]
            try:
                plugin_name, module = self._load_plugin_module(plugin_dir, filename)
                if not self._register_plugin(plugin_name, module):
                    self.logger.warning(f"插件 {plugin_name} 缺少 TRIGGHT_KEYWORD 或 on_message")
                self._register_plugin_background_task(plugin_name, module)
            except Exception as e:
                self.logger.error(f"加载插件 {plugin_name} 失败: {e}")
                self.logger.error(traceback.format_exc())

        self._plugins.sort(key=lambda p: (p['is_any'], -len(p['keyword']), p['name']))
        self.logger.info(f"插件加载完成: {len(self._plugins)} 个命令插件, {len(self._plugins_bg_tasks)} 个后台任务")

    async def _start_plugin_background_tasks(self):
        """启动所有插件的后台任务"""
        for bg in self._plugins_bg_tasks:
            self.logger.info(f"启动插件后台任务: {bg['name']}")
            asyncio.create_task(bg['task'](self))

    async def _try_plugins(self, message: Any, order: str, skip_plugins: Optional[set] = None) -> bool:
        """
        尝试匹配并执行插件

        Args:
            message: 消息对象
            order: 用户命令
            skip_plugins: 需要跳过的插件名称集合 (None 表示不跳过)

        Returns:
            bool: 是否有插件处理了消息
        """
        skip_plugins = skip_plugins or set()
        order = order.strip()
        if not order:
            return False

        for plugin in self._plugins:
            if plugin['name'] in skip_plugins:
                continue
            if not plugin['is_any'] and not order.startswith(plugin['keyword']):
                continue

            log_action = "尝试" if plugin['is_any'] else "匹配到"
            self.logger.info(f"[插件] {log_action}插件: {plugin['name']}, 关键字: {plugin['keyword']}")
            result = await self._execute_plugin(plugin, message, order)
            if result:
                return True

        return False

    def _create_plugin_compat_objects(self):
        class FakeManager:
            class Message:
                def __init__(self, *args):
                    self.parts = args
                def __iter__(self):
                    return iter(self.parts)

        class FakeSegments:
            class Text:
                def __init__(self, text):
                    self.text = str(text)
                def __str__(self):
                    return self.text

            class At:
                def __init__(self, user_id):
                    self.user_id = user_id
                def __str__(self):
                    return f"@{self.user_id}"

            class Image:
                def __init__(self, url):
                    self.url = url
                    self.file = url

            class Reply:
                def __init__(self, msg_id):
                    self.id = msg_id

        class FakeEvents:
            class GroupMessageEvent: pass
            class PrivateMessageEvent: pass

        return FakeManager, FakeSegments, FakeEvents

    def _build_plugin_kwargs(self, plugin: dict, message: Any, order: str) -> dict:
        adapted_event = self._adapt_message_for_plugin(message, order)
        actions = self._create_plugin_actions(message)
        manager, segments, events = self._create_plugin_compat_objects()
        cooldowns = {}

        available = {
            'event': adapted_event,
            'actions': actions,
            'Manager': manager,
            'Segments': segments,
            'Events': events,
            'reminder': self.reminder,
            'bot_name': self.bot_name,
            'order': order,
            'ROOT_User': self.root_users,
            'Super_User': [],
            'Manage_User': [],
            'config': self.config,
            'time': time,
            'cooldowns': cooldowns,
            'plugins': self._plugins,
            'plugin_categories': self.PLUGIN_CATEGORIES,
            'client': self,
        }

        sig = inspect.signature(plugin['on_message'])
        kwargs = {name: available[name] for name in sig.parameters if name in available}
        has_var_kwargs = any(p.kind == inspect.Parameter.VAR_KWARGS for p in sig.parameters.values())
        if has_var_kwargs:
            kwargs.update({key: value for key, value in available.items() if key not in kwargs})
        return kwargs

    async def _execute_plugin(self, plugin: dict, message: Any, order: str) -> bool:
        """执行单个插件"""
        try:
            result = await plugin['on_message'](**self._build_plugin_kwargs(plugin, message, order))
            if result:
                self.logger.info(f"[插件] {plugin['name']} 处理了消息")
                return True
            return False
        except Exception as e:
            self.logger.error(f"执行插件 {plugin['name']} 错误: {e}")
            self.logger.error(traceback.format_exc())
            return False

    def _adapt_message_for_plugin(self, message: Any, content: str):
        """为插件创建适配的事件对象"""
        class AdaptedEvent:
            def __init__(self, msg, text):
                self.message = text
                self.user_id = getattr(msg.author, 'member_openid', 'unknown')
                self.group_id = getattr(msg, 'group_openid', None)
                self.message_id = getattr(msg, 'id', None)
                self.self_id = None
        return AdaptedEvent(message, content)

    def _create_plugin_actions(self, message: Any):
        """为插件创建 actions 对象"""
        client = self

        class PluginActions:
            def __init__(self):
                self._message = message
                self._client = client

            async def send(self, **kwargs):
                markdown = kwargs.get('markdown')
                if markdown:
                    await client._send_message(message, markdown=markdown)
                    return
                msg = kwargs.get('content') or kwargs.get('message')
                if msg:
                    content = self._extract_text(msg)
                    if content:
                        await client._send_message(message, content)

            async def send_file(self, url: str, file_type: int = 1):
                group_openid = getattr(self._message, 'group_openid', None)
                try:
                    if group_openid:
                        await self._client.api.post_group_file(
                            group_openid=group_openid,
                            file_type=file_type,
                            url=url,
                            srv_send_msg=True,
                        )
                    else:
                        await self._client.api.post_c2c_file(
                            openid=self._message.author.user_openid,
                            file_type=file_type,
                            url=url,
                            srv_send_msg=True,
                        )
                except Exception as e:
                    self._client.logger.error(f"发送文件失败: {e}")
                    await self.send(content=f"发送文件失败: {e}")

            async def send_help_image(self, help_text: str):
                sent = await client._send_help_image(self._message, help_text)
                if not sent:
                    await self.send(content=help_text)

            def _extract_text(self, msg):
                if isinstance(msg, str):
                    return msg
                if hasattr(msg, '__iter__'):
                    parts = []
                    for part in msg:
                        if hasattr(part, 'text'):
                            parts.append(part.text)
                        elif isinstance(part, str):
                            parts.append(part)
                    return ''.join(parts)
                return str(msg) if msg else ''

            async def get_group_member_info(self, group_id, user_id):
                class MemberInfo:
                    def __init__(self):
                        self.data = type('data', (), {'raw': {'card': '', 'nickname': '用户', 'user_id': user_id}})()
                return MemberInfo()

            async def get_stranger_info(self, user_id):
                class StrangerInfo:
                    def __init__(self):
                        self.data = type('data', (), {'raw': {'nickname': '用户', 'user_id': user_id}})()
                return StrangerInfo()

            async def get_msg(self, msg_id):
                class FakeMsg:
                    data = {'message': []}
                return FakeMsg()

            async def del_message(self, msg_id):
                pass

            async def set_msg_emoji_like(self, **kwargs):
                return {'status': 'ok'}

            @property
            def custom(self):
                class Custom:
                    async def set_msg_emoji_like(self, **kwargs):
                        return {'status': 'ok'}
                return Custom()

        return PluginActions()

    # ==================== 统一消息发送 ====================

    async def _send_message(self, message, content=None, msg_type=0, markdown=None):
        """
        发送消息，自动识别消息类型（单聊/群聊）

        Args:
            message: 原消息对象
            content: 消息内容
            msg_type: 消息类型 (0=文本, 2=markdown, 3=ark, 4=embed)
            markdown: Markdown 内容字典 (如 {"content": "markdown文本"})
        """
        group_openid = getattr(message, 'group_openid', None)
        try:
            if group_openid:
                kwargs = {
                    "group_openid": group_openid,
                    "msg_id": message.id,
                    "msg_seq": str(int(time.time() * 1000000) % 100000000),
                }
                api_method = self.api.post_group_message
                display_prefix = f"群 {group_openid}"
            else:
                kwargs = {
                    "openid": message.author.user_openid,
                    "msg_id": message.id,
                }
                api_method = self.api.post_c2c_message
                display_prefix = f"单聊 {message.author.user_openid}"

            if markdown:
                kwargs["msg_type"] = 2
                kwargs["markdown"] = markdown
                display_text = markdown.get("content", "")[:100]
            elif content and self._has_markdown_syntax(content):
                kwargs["msg_type"] = 2
                kwargs["markdown"] = {"content": content}
                display_text = content[:100]
            else:
                kwargs["msg_type"] = msg_type
                kwargs["content"] = content or ""
                display_text = (content or "")[:100]

            self.logger.info(f"[发送消息] {display_prefix}: {display_text}...")
            await api_method(**kwargs)
        except Exception as e:
            self.logger.error(f"发送消息失败: {e}")

    # ==================== 帮助消息发送 ====================

    async def _send_help_image(self, message, help_text: str) -> bool:
        """发送格式化的 Markdown 帮助文本到当前会话。"""
        try:
            await self._send_message(message, help_text)
            return True
        except Exception as e:
            self.logger.error(f"发送帮助消息失败: {e}")
            return False

    # ==================== 统一命令处理 ====================

    async def _reply(self, message, content=None, markdown=None):
        """统一的回复接口，自动适配消息类型"""
        if hasattr(message, 'reply'):
            await message.reply(content=content, markdown=markdown or {})
        else:
            await self._send_message(message, content, markdown=markdown)

    async def _handle_ping(self, message):
        await self._reply(message, content="Ciallo∼(∠・ω[ )⌒☆")

    async def _handle_help_command(self, message):
        help_text = self._get_help_text()
        sent = await self._send_help_image(message, help_text)
        if not sent:
            await self._reply(message, content=help_text)

    async def _handle_status_command(self, message):
        status = self._get_status_text()
        if hasattr(message, 'reply'):
            await message.reply(markdown={"content": status})
        else:
            await self._send_message(message, status)

    async def _handle_ai_chat(self, message, order, user_id, user_name, use_markdown=False):
        """统一的 AI 对话处理"""
        send_func = lambda text: (
            message.reply(markdown={"content": text}) if use_markdown
            else self._send_message(message, text)
        )
        await self.ai_chat.handle_message(order, user_id, user_name, send_func)

    # ==================== 单聊消息处理 ====================

    async def on_c2c_message_create(self, message: Any):
        """
        处理 QQ 单聊消息 (C2C_MESSAGE_CREATE)
        """
        self.logger.info(f"[EVENT] on_c2c_message_create triggered")
        try:
            content = message.content.strip() if message.content else ""
            user_openid = message.author.user_openid

            nickname = self._try_get_nickname(message)
            user_label = f"{nickname}({user_openid})" if nickname else user_openid
            self.logger.info(f"[单聊] 用户 {user_label}: {content}")

            if not content:
                await self._send_message(message, f"你好呀~ 我是{self.bot_name}，有什么可以帮你的吗？")
                return

            if content.lower() == "ping":
                await self._handle_ping(message)
                return

            if content in ("帮助", f"{self.reminder}帮助"):
                await self._handle_help_command(message)
                return

            if content in ("状态", f"{self.reminder}状态"):
                await self._handle_status_command(message)
                return

            if not self.allow_ai:
                await self._send_message(message, f"未找到相关指令")
                return

            if content.startswith(self.reminder):
                order = content[len(self.reminder):].strip()
                if len(order) >= 2:
                    await self._handle_ai_chat(message, order, user_openid, "用户")
                    return

            if len(content) >= 1:
                await self._handle_ai_chat(message, content, user_openid, "用户")

        except Exception:
            self.logger.error(f"处理单聊消息错误: {traceback.format_exc()}")
            try:
                await self._send_message(message, f"{self.bot_name}发生错误了，请稍后再试")
            except Exception:
                pass

    # ==================== 群聊消息处理（仅插件） ====================

    def _try_get_nickname(self, message) -> str:
        """尝试获取用户昵称"""
        try:
            return message.author.username or ""
        except AttributeError:
            return ""

    def _strip_mention(self, content: str) -> str:
        """移除消息中的 @机器人 前缀"""
        if content.startswith(f"<@!{self.robot.id}>"):
            return content[len(f"<@!{self.robot.id}>"):].strip()
        elif content.startswith(f"<@{self.robot.id}>"):
            return content[len(f"<@{self.robot.id}>"):].strip()
        return content

    async def on_group_at_message_create(self, message: Any):
        """
        处理 QQ 群聊@机器人消息 (GROUP_AT_MESSAGE_CREATE)
        """
        self.logger.info(f"[EVENT] on_group_at_message_create triggered")
        try:
            content = message.content.strip() if message.content else ""
            member_openid = message.author.member_openid
            group_openid = message.group_openid

            content = self._strip_mention(content)

            nickname = self._try_get_nickname(message)
            user_label = f"{nickname}({member_openid})" if nickname else member_openid
            self.logger.info(f"[群聊] 群 {group_openid} 用户 {user_label}: {content}")

            if not content:
                await self._send_message(message, f"发送 @机器人 /帮助 查看可用指令")
                return

            order = content
            if order.startswith("+") or order.startswith("/"):
                order = order[1:].strip()

            if order.lower() == "ping":
                await self._handle_ping(message)
                return

            if order == "帮助":
                await self._handle_help_command(message)
                return

            if order == "状态":
                await self._handle_status_command(message)
                return

            plugin_result = await self._try_plugins(message, order)
            if plugin_result:
                return

            if content and not content.startswith(self.reminder):
                await self._send_message(message, f"未找到匹配的插件命令，发送 @机器人 /帮助 查看可用指令")

        except Exception:
            self.logger.error(f"处理群聊消息错误: {traceback.format_exc()}")
            try:
                await self._send_message(message, f"{self.bot_name}发生错误了，请稍后再试")
            except Exception:
                pass

    async def on_group_message_create(self, message: Any):
        """
        处理群聊全量消息 (GROUP_MESSAGE_CREATE)
        """
        self.logger.info(f"[EVENT] on_group_message_create triggered")
        try:
            content = message.content.strip() if message.content else ""
            member_openid = message.author.member_openid
            group_openid = message.group_openid

            nickname = self._try_get_nickname(message)
            user_label = f"{nickname}({member_openid})" if nickname else member_openid
            self.logger.info(f"[群聊全量] 群 {group_openid} 用户 {user_label}: {content}")

            if not content:
                return

            raw_content = content
            content = re.sub(r'<@!?\w+>', '', content).strip()
            if not content:
                return

            order = content
            if order.startswith("+") or order.startswith("/"):
                order = order[1:].strip()

            if order.lower() == "ping":
                await self._handle_ping(message)
                return

            if order == "帮助":
                await self._handle_help_command(message)
                return

            if order == "状态":
                await self._handle_status_command(message)
                return

            plugin_result = await self._try_plugins(message, order, skip_plugins={"affection"})
            if plugin_result:
                return

            if raw_content.startswith(self.reminder):
                await self._send_message(message, f"未找到匹配的插件命令，发送 @机器人 /帮助 查看可用指令")

        except Exception:
            self.logger.error(f"处理群聊全量消息错误: {traceback.format_exc()}")
            try:
                await self._send_message(message, f"{self.bot_name}发生错误了，请稍后再试")
            except Exception:
                pass

    # ==================== 频道私信处理 ====================

    async def on_direct_message_create(self, message: DirectMessage):
        """
        处理频道私信消息 (DIRECT_MESSAGE_CREATE)
        """
        try:
            content = message.content.strip() if message.content else ""
            user_id = message.author.id

            nickname = self._try_get_nickname(message)
            user_label = f"{nickname}({user_id})" if nickname else user_id
            self.logger.info(f"[频道私信] 用户 {user_label}: {content}")

            if not content:
                await message.reply(content=f"你好呀~ 我是{self.bot_name}，有什么可以帮你的吗？")
                return

            if content.lower() == "ping":
                await self._handle_ping(message)
                return

            if content in ("帮助", f"{self.reminder}帮助"):
                await self._handle_help_command(message)
                return

            if not self.allow_ai:
                await message.reply(content=f"未找到相关指令")
                return

            if content.startswith(self.reminder):
                order = content[len(self.reminder):].strip()
                if len(order) >= 2:
                    await self._handle_ai_chat(message, order, user_id, message.author.username, use_markdown=True)
                    return

            if len(content) >= 2:
                await self._handle_ai_chat(message, content, user_id, message.author.username, use_markdown=True)

        except Exception:
            self.logger.error(f"处理频道私信错误: {traceback.format_exc()}")
            try:
                await message.reply(content=f"{self.bot_name}发生错误了，请稍后再试")
            except Exception:
                pass

    # ==================== 频道消息处理 ====================

    async def on_at_message_create(self, message: Message):
        """
        处理频道@机器人消息 (AT_MESSAGE_CREATE)
        """
        try:
            content = message.content.strip() if message.content else ""
            user_id = message.author.id

            content = self._strip_mention(content)

            nickname = self._try_get_nickname(message)
            user_label = f"{nickname}({user_id})" if nickname else user_id
            self.logger.info(f"[频道] 频道 {message.channel_id} 用户 {user_label}: {content}")

            if not content:
                help_text = self._get_help_text()
                sent = await self._send_help_image(message, help_text)
                if not sent:
                    await message.reply(content=help_text)
                return

            if content.lower() == "ping":
                await self._handle_ping(message)
                return

            if content in ("帮助", f"{self.reminder}帮助"):
                await self._handle_help_command(message)
                return

            if content in ("状态", f"{self.reminder}状态"):
                await self._handle_status_command(message)
                return

            if not self.allow_ai:
                await message.reply(content=f"未找到相关指令")
                return

            if content.startswith(self.reminder):
                order = content[len(self.reminder):].strip()
                if len(order) >= 2:
                    await self._handle_ai_chat(message, order, user_id, message.author.username, use_markdown=True)
                    return

        except Exception:
            self.logger.error(f"处理频道消息错误: {traceback.format_exc()}")
            try:
                await message.reply(content=f"{self.bot_name}发生错误了，请稍后再试")
            except Exception:
                pass

    # ==================== 事件监听 ====================

    async def on_group_add_robot(self, group: Any):
        self.logger.info(f"机器人被添加到群: {group.group_openid if hasattr(group, 'group_openid') else 'unknown'}")

    async def on_group_del_robot(self, group: Any):
        self.logger.info(f"机器人被移出群: {group.group_openid if hasattr(group, 'group_openid') else 'unknown'}")

    async def on_group_msg_reject(self, group: Any):
        self.logger.info(f"群消息被拒绝: {group.group_openid if hasattr(group, 'group_openid') else 'unknown'}")

    async def on_group_msg_receive(self, group: Any):
        self.logger.info(f"群消息接收恢复: {group.group_openid if hasattr(group, 'group_openid') else 'unknown'}")

    async def on_friend_add(self, user: Any):
        self.logger.info(f"好友添加: {user.user_openid if hasattr(user, 'user_openid') else 'unknown'}")

    async def on_friend_del(self, user: Any):
        self.logger.info(f"好友删除: {user.user_openid if hasattr(user, 'user_openid') else 'unknown'}")

    # ==================== AI 对话处理 ====================
    # 委托给 self.ai_chat (ai/chat.py)
    # 角色系统委托给 self.role_manager (ai/role_manager.py)

    @staticmethod
    def _has_markdown_syntax(text: str) -> bool:
        """检测文本是否包含 Markdown 语法"""
        if not text:
            return False
        lines = text.split('\n')
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(('# ', '## ', '### ', '#### ', '##### ', '###### ')):
                return True
            if stripped.startswith('- ') or stripped.startswith('* '):
                return True
            if stripped.startswith(('1. ', '2. ', '3. ')):
                return True
            if stripped.startswith('> '):
                return True
            if stripped.startswith('```'):
                return True
            if stripped in ('---', '***', '___'):
                return True
        if '**' in text or '__' in text or '*' in text:
            return True
        if '`' in text:
            return True
        if '[[' in text and ']]' in text:
            return True
        if '[' in text and '](' in text:
            return True
        return False

    # 插件分类映射：分类名 -> 该分类下插件名列表
    PLUGIN_CATEGORIES = [
        ("🎯 签到系统", ["checkin", "affection"]),
        ("🌤️ 生活工具", ["weather", "ping", "hitokoto", "domain_whois", "httptest"]),
        ("🎨 娱乐工具", ["acg_picture", "qr_code", "mc_status"]),
        ("🎭 角色扮演", ["roleplay"]),
        ("📺 直播监控", ["kick"]),
    ]

    def _get_help_text(self) -> str:
        """动态生成帮助文本"""
        lines = [f"## 📖 {self.bot_name} 帮助", ""]
        lines.append("### 💡 群聊指令格式")
        lines.append("- **@机器人 /指令** - 执行指令")
        lines.append("")
        lines.append("### 🎮 内置指令")
        lines.append("")
        lines.append("**📋 帮助**")
        lines.append("- **@机器人 /帮助** - 显示此帮助")
        lines.append("- **@机器人 /状态** - 查看状态")
        lines.append("")

        plugin_help_map = {p['name']: p['help'] for p in self._plugins}

        for cat_name, plugin_names in self.PLUGIN_CATEGORIES:
            matched = {name: plugin_help_map[name] for name in plugin_names if name in plugin_help_map}
            if not matched:
                continue
            lines.append(f"**{cat_name}**")
            for name, help_msg in matched.items():
                lines.append(f"- **@机器人 /{help_msg}**")
            lines.append("")

        lines.append(f"> 📝 版本: **{self.version_name}**")
        return "\n".join(lines)

    def _get_status_text(self) -> str:
        """获取状态文本"""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            memory_text = f"{memory.percent}%"
        except Exception:
            cpu = "N/A"
            memory_text = "N/A"

        return f"""## 📊 {self.bot_name} 状态

### 系统信息
- **CPU**: {cpu}%
- **内存**: {memory_text}

### AI 配置
- **AI 模型**: {self.context.EnableNetwork}
- **版本**: {self.version_name}"""
