# -*- coding: utf-8 -*-

import base64
import importlib.util
import inspect
import json
import os
import time
import traceback
from typing import Any, Optional

from core.context import PluginContext
from core.permissions import is_root
from Tools.scheduler import get_scheduler

PLUGIN_CATEGORIES = [
    ("🎯 签到系统", ["checkin", "affection"]),
    ("🌤️ 生活工具", ["weather", "ping", "hitokoto", "domain_whois", "httptest"]),
    ("🎨 娱乐工具", ["acg_picture", "qr_code", "mc_status"]),
    ("📺 直播监控", ["kick"]),
]


class PluginManager:

    def __init__(self, client):
        self.client = client
        self.logger = client.logger
        self.plugins = []
        self.plugins_help = {}

    @staticmethod
    def is_plugin_file(filename: str) -> bool:
        return filename.endswith(".py") and not filename.startswith(("__", "d_"))

    def load_module(self, plugin_dir: str, filename: str):
        plugin_name = filename[:-3]
        plugin_path = os.path.join(plugin_dir, filename)
        spec = importlib.util.spec_from_file_location(f"plugins.{plugin_name}", plugin_path)
        if not spec or not spec.loader:
            raise ImportError(f"无法创建插件加载规范: {filename}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return plugin_name, module

    def register(self, plugin_name: str, module) -> bool:
        help_msg = getattr(module, 'HELP_MESSAGE', '')
        on_message = getattr(module, 'on_message', None)
        if not callable(on_message):
            return False

        keywords = getattr(module, 'TRIGGER_KEYWORDS', None) or getattr(module, 'TRIGGHT_KEYWORDS', None)
        if keywords:
            keywords = [str(k).strip() for k in keywords if str(k).strip()]
        else:
            keyword = getattr(module, 'TRIGGER_KEYWORD', None) or getattr(module, 'TRIGGHT_KEYWORD', None)
            keywords = [keyword.strip()] if keyword and keyword.strip() else []
        if not keywords:
            return False

        keyword = keywords[0]
        self.plugins.append({
            'name': plugin_name,
            'keyword': keyword,
            'keywords': keywords,
            'help': help_msg,
            'module': module,
            'on_message': on_message,
            'is_any': 'Any' in keywords,
        })
        self.plugins_help[plugin_name] = help_msg
        self.logger.info(f"加载插件: {plugin_name} ({'/'.join(keywords)})")
        return True

    def register_scheduled_jobs(self, plugin_name: str, module) -> bool:
        register_fn = getattr(module, 'register_scheduled_jobs', None)
        if callable(register_fn):
            register_fn(get_scheduler())
            self.logger.info(f"插件 {plugin_name} 注册定时任务")
            return True
        return False

    def load_plugins(self, plugin_dir: Optional[str] = None, enabled_map: Optional[dict] = None):
        plugin_dir = plugin_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plugins")
        self.plugins.clear()
        self.plugins_help.clear()

        if not os.path.exists(plugin_dir):
            self.logger.warning(f"插件目录不存在: {plugin_dir}")
            return

        if enabled_map is None:
            enabled_map = self._read_enabled_map()

        for filename in sorted(os.listdir(plugin_dir)):
            if not self.is_plugin_file(filename):
                continue

            plugin_name = filename[:-3]
            if enabled_map.get(plugin_name, True) is False:
                self.logger.info(f"插件 {plugin_name} 已被 webadmin 禁用，跳过")
                continue
            try:
                plugin_name, module = self.load_module(plugin_dir, filename)
                registered = self.register(plugin_name, module)
                has_scheduled = self.register_scheduled_jobs(plugin_name, module)
                if not registered and not has_scheduled:
                    self.logger.warning(f"插件 {plugin_name} 缺少 TRIGGER_KEYWORD/on_message 且无 register_scheduled_jobs，已跳过")
            except Exception as e:
                self.logger.error(f"加载插件 {plugin_name} 失败: {e}")
                self.logger.error(traceback.format_exc())

        self.plugins.sort(key=lambda p: (p['is_any'], -max(len(k) for k in p['keywords']), p['name']))
        self.logger.info(f"插件加载完成: {len(self.plugins)} 个命令插件")

    def _read_enabled_map(self) -> dict:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "plugins_enabled.json")
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            pass
        return {}

    def reload(self, plugin_dir: Optional[str] = None):
        self.load_plugins(plugin_dir=plugin_dir)

    async def try_plugins(self, message: Any, order: str, skip_plugins: Optional[set] = None) -> bool:
        skip_plugins = skip_plugins or set()
        order = order.strip()
        if not order:
            return False

        for plugin in self.plugins:
            if plugin['name'] in skip_plugins:
                continue
            if not plugin['is_any'] and not any(order.startswith(kw) for kw in plugin['keywords']):
                continue

            log_action = "尝试" if plugin['is_any'] else "匹配到"
            self.logger.info(f"[插件] {log_action}插件: {plugin['name']}, 关键字: {'/'.join(plugin['keywords'])}")
            result = await self.execute(plugin, message, order)
            if result:
                return True

        return False

    def get_help_text(self, bot_name: str, version_name: str) -> str:
        lines = [f"## 📖 {bot_name} 帮助", ""]
        lines.append("### 💡 群聊指令格式")
        lines.append("- **@机器人 /指令** - 执行指令")
        lines.append("")
        lines.append("### 🎮 内置指令")
        lines.append("")
        lines.append("**📋 帮助**")
        lines.append("- **@机器人 /帮助** - 显示此帮助")
        lines.append("- **@机器人 /状态** - 查看状态")
        lines.append("")
        lines.append("**🎭 角色扮演**")
        lines.append("- **@机器人 /角色 列表** - 查看可用角色")
        lines.append("- **@机器人 /角色 切换 <名称>** - 切换角色")
        lines.append("- **@机器人 /角色 创建 <名称> [提示词]** - 创建自定义角色")
        lines.append("")

        plugin_help_map = {p['name']: p['help'] for p in self.plugins}

        for cat_name, plugin_names in PLUGIN_CATEGORIES:
            matched = {name: plugin_help_map[name] for name in plugin_names if name in plugin_help_map}
            if not matched:
                continue
            lines.append(f"**{cat_name}**")
            for name, help_msg in matched.items():
                lines.append(f"- **@机器人 /{help_msg}**")
            lines.append("")

        lines.append(f"> 📝 版本: **{version_name}**")
        return "\n".join(lines)


    def create_compat_objects(self):
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
            class GroupMessageEvent:
                pass

            class PrivateMessageEvent:
                pass

        return FakeManager, FakeSegments, FakeEvents

    def adapt_message_for_plugin(self, message: Any, content: str):
        nickname = self.client._try_get_nickname(message)
        class AdaptedEvent:
            def __init__(self, msg, text):
                self.message = text
                self.user_id = getattr(msg.author, 'member_openid', 'unknown')
                self.nickname = nickname
                self.group_id = getattr(msg, 'group_openid', None)
                self.message_id = getattr(msg, 'id', None)
                self.self_id = None
        return AdaptedEvent(message, content)

    def create_plugin_actions(self, message: Any):
        client = self.client

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

            async def send_file(self, url: Optional[str] = None, file_type: int = 1,
                                file=None, filename: Optional[str] = None):
                try:
                    if file is not None and hasattr(file, 'read'):
                        data = file.read()
                    elif url:
                        resp = await client.http_client.get(url)
                        resp.raise_for_status()
                        data = resp.content
                    else:
                        raise ValueError("必须提供 url 或 file 参数")

                    file_b64 = base64.b64encode(data).decode("utf-8")
                    from qqbot_openapi import Route
                    group_openid = getattr(self._message, 'group_openid', None)
                    payload = {
                        "file_type": file_type,
                        "file_data": file_b64,
                        "srv_send_msg": True,
                    }
                    if group_openid:
                        route = Route("POST", "/v2/groups/{group_openid}/files",
                                     group_openid=group_openid)
                    else:
                        route = Route("POST", "/v2/users/{openid}/files",
                                     openid=self._message.author.user_openid)
                    await self._client.api._http.request(route, json=payload)
                    self._client.logger.info(f"文件发送成功: {filename or url or '(bytesio)'}")
                except Exception as e:
                    self._client.logger.error(f"发送文件失败: {e}")

            async def send_local_file(self, file_path: str, file_type: int = 1):
                try:
                    with open(file_path, "rb") as f:
                        file_b64 = base64.b64encode(f.read()).decode("utf-8")
                    from qqbot_openapi import Route
                    group_openid = getattr(self._message, 'group_openid', None)
                    payload = {
                        "file_type": file_type,
                        "file_data": file_b64,
                        "srv_send_msg": True,
                    }
                    if group_openid:
                        route = Route("POST", "/v2/groups/{group_openid}/files", group_openid=group_openid)
                    else:
                        route = Route("POST", "/v2/users/{openid}/files", openid=self._message.author.user_openid)
                    await self._client.api._http.request(route, json=payload)
                    self._client.logger.info(f"本地文件发送成功: {os.path.basename(file_path)}")
                except Exception as e:
                    self._client.logger.error(f"发送本地文件失败: {e}")

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
                    data: dict = {'message': []}
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

    def _build_compat(self, message: Any, order: str) -> dict:
        adapted_event = self.adapt_message_for_plugin(message, order)
        actions = self.create_plugin_actions(message)
        manager, segments, events = self.create_compat_objects()
        cooldowns: dict = {}

        return {
            'event': adapted_event,
            'actions': actions,
            'Manager': manager,
            'Segments': segments,
            'Events': events,
            'reminder': self.client.reminder,
            'bot_name': self.client.bot_name,
            'order': order,
            'ROOT_User': self.client.root_users,
            'is_root': lambda user_id: is_root(user_id, self.client.config),
            'Super_User': [],
            'Manage_User': [],
            'config': self.client.config,
            'time': time,
            'cooldowns': cooldowns,
            'plugins': self.plugins,
            'plugin_categories': PLUGIN_CATEGORIES,
            'client': self.client,
        }

    def build_context(self, plugin: dict, message: Any, order: str):
        compat = self._build_compat(message, order)
        return PluginContext(self.client, message, order, compat['event'], compat['actions'], compat)

    def build_kwargs(self, plugin: dict, message: Any, order: str) -> dict:
        available = self._build_compat(message, order)
        sig = inspect.signature(plugin['on_message'])
        kwargs = {name: available[name] for name in sig.parameters if name in available}
        has_var_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
        if has_var_kwargs:
            kwargs.update({key: value for key, value in available.items() if key not in kwargs})
        return kwargs

    @staticmethod
    def is_new_api(plugin: dict) -> bool:
        params = list(inspect.signature(plugin['on_message']).parameters.values())
        return len(params) == 1 and params[0].name in ('ctx', 'context')

    async def execute(self, plugin: dict, message: Any, order: str) -> bool:
        try:
            if self.is_new_api(plugin):
                result = await plugin['on_message'](self.build_context(plugin, message, order))
            else:
                result = await plugin['on_message'](**self.build_kwargs(plugin, message, order))
            if result:
                self.logger.info(f"[插件] {plugin['name']} 处理了消息")
                return True
            return False
        except Exception as e:
            self.logger.error(f"执行插件 {plugin['name']} 错误: {e}")
            self.logger.error(traceback.format_exc())
            return False
