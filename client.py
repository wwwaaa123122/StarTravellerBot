# -*- coding: utf-8 -*-
"""
QQ 开放平台机器人客户端：消息分发 + AI 调用 + 插件调度。
场景流程见 core/dispatcher.py，插件系统见 core/plugin_manager.py。
"""

import os
import sys
import asyncio
import traceback
from typing import Any, Dict

from qqbot_openapi import logging
from qqbot_openapi import Message, DirectMessage
from qqbot_openapi import Client as QQClient, Intents

CONTACT_URL = "https://xc-lr.cn/about"

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from Tools.core import BotContext, VERSION_NAME
from Tools.rag_memory import RAGMemory
from Tools.scheduler import get_scheduler, set_client, shutdown as shutdown_scheduler
from ai.role_manager import RoleManager
from ai.chat import AIChat
from core.http import create_http_client
from core.plugin_manager import PluginManager
from core.messenger import Messenger
from core.stats import StatsTracker
from core.dispatcher import Dispatcher, SCENE_C2C, SCENE_GROUP_AT, SCENE_GROUP, SCENE_DIRECT, SCENE_AT


class XCLRClient(QQClient):
    """
    星辰旅人 QQ 开放平台机器人客户端

    支持的场景:
    1. QQ 单聊 (C2C_MESSAGE_CREATE)
    2. QQ 群聊@机器人 (GROUP_AT_MESSAGE_CREATE)
    3. 频道私信 (DIRECT_MESSAGE_CREATE)
    4. 频道@机器人 (AT_MESSAGE_CREATE)
    """

    def __init__(self, config: Dict[str, Any], **kwargs):
        """初始化机器人客户端。"""
        intents = Intents(
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

        self.context = BotContext()
        self.context.EnableNetwork = others.get("default_mode", "Ds")

        self.allow_ai = others.get("allow_ai", True)

        self.rag = RAGMemory(os.path.join(PROJECT_ROOT, "data"))

        self.logger = logging.get_logger()

        self.role_manager = RoleManager()

        self.stats = StatsTracker(logger=self.logger)
        self.messenger = Messenger(self)
        self.plugin_manager = PluginManager(self)
        self.dispatcher = Dispatcher(self)

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
    def http_client(self):
        if not hasattr(self, '_http_client_instance') or self._http_client_instance.is_closed:
            self._http_client_instance = create_http_client()
        return self._http_client_instance

    async def close(self):
        shutdown_scheduler()
        if hasattr(self, '_http_client_instance') and not self._http_client_instance.is_closed:
            await self._http_client_instance.aclose()
        await super().close()

    async def on_ready(self):
        self.logger.info(f"{'='*50}")
        self.logger.info(f"{self.bot_name} 已上线!")
        self.logger.info(f"Version: {self.version_name}")
        self.logger.info(f"AI 模型: {self.context.EnableNetwork}")
        self.logger.info(f"AI 对话: {'开启' if self.allow_ai else '关闭'}")
        self.logger.info(f"{'='*50}")

        self.plugin_manager.load_plugins()
        await self._start_scheduler()
        asyncio.create_task(self._watch_plugin_reload())

    async def _watch_plugin_reload(self):
        """监听 data/reload.flag（webadmin 写入），触发插件热重载。"""
        flag = os.path.join(PROJECT_ROOT, "data", "reload.flag")
        while True:
            await asyncio.sleep(10)
            if not os.path.exists(flag):
                continue
            try:
                self.plugin_manager.reload()
                self.logger.info("插件热重载完成")
            except Exception as e:
                self.logger.error(f"插件热重载失败: {e}")
            finally:
                try:
                    os.unlink(flag)
                except OSError:
                    pass

    async def _start_scheduler(self):
        """启动 APScheduler 调度器，注入客户端引用。"""
        scheduler = get_scheduler()
        set_client(self)
        scheduler.start()
        self.logger.info(f"调度器已启动，共 {len(scheduler.get_jobs())} 个定时任务")

    async def _send_message(self, message, content=None, msg_type=0, markdown=None):
        await self.messenger.send_message(message, content, msg_type, markdown)

    async def _send_help_image(self, message, help_text: str) -> bool:
        return await self.messenger.send_help_image(message, help_text)

    async def _reply(self, message, content=None, markdown=None):
        await self.messenger.reply(message, content, markdown)

    def _strip_mention(self, content: str) -> str:
        return self.messenger.strip_mention(content)

    async def _handle_ping(self, message):
        await self._reply(message, content="Ciallo∼(∠・ω[ )⌒☆")

    async def _handle_help_command(self, message):
        help_text = self.plugin_manager.get_help_text(self.bot_name, self.version_name)
        sent = await self._send_help_image(message, help_text)
        if not sent:
            await self._reply(message, content=help_text)

    async def _handle_status_command(self, message):
        status = self._get_status_text()
        if hasattr(message, 'reply'):
            await message.reply(markdown={"content": status})
        else:
            await self._send_message(message, status)

    async def _handle_roleplay_command(self, message, content) -> bool:
        """处理角色扮演命令（集成到主程序而非插件系统）"""
        if not content.startswith("角色"):
            return False

        from ai.roleplay import on_message as roleplay_on_message
        kwargs = self.plugin_manager.build_kwargs({'on_message': roleplay_on_message}, message, content)
        # kwargs 已含 event/actions，直接展开避免重复传参
        return await roleplay_on_message(**kwargs)

    async def _handle_ai_chat(self, message, order, user_id, user_name, use_markdown=False):
        """统一的 AI 对话处理（支持 Function Calling）"""
        async def execute_tool(tool_name, arguments):
            from ai.function_calling import execute_tool
            return await execute_tool(tool_name, arguments, user_id,
                                      self.root_users, self.config, self)
        try:
            result = await self.ai_chat.run_with_tools(
                user_id, user_name, order, execute_tool, self.root_users)
            if result:
                usage = self.ai_chat._last_usage or {}
                self.stats.record_ai_call(usage.get("total_tokens", 0))
                if use_markdown:
                    await message.reply(markdown={"content": result})
                else:
                    await self._send_message(message, result)
                    asyncio.create_task(self._try_send_tts(message, result))
            else:
                await self._send_message(message, "AI 服务暂时不可用")
        except Exception as e:
            self.logger.error(f"AI 对话错误: {traceback.format_exc()}")
            self.logger.error(f"AI 对话错误: {e}")
            await self._send_message(message, f"AI 服务异常，请稍后再试\n联系管理员: {CONTACT_URL}")

    async def _try_send_tts(self, message, text: str):
        """尝试为 AI 回复生成并发送语音"""
        try:
            from plugins.tts import sanitize_for_tts, _generate_tts
            import gc

            clean = sanitize_for_tts(text)
            if not clean or len(clean) > 200:
                return

            audio_path = await _generate_tts(clean, self.config)
            if audio_path:
                actions = self.plugin_manager.create_plugin_actions(message)
                await actions.send_local_file(audio_path, file_type=3)
                await asyncio.sleep(1)
                if os.path.exists(audio_path):
                    os.unlink(audio_path)
                del actions
                gc.collect()
        except ImportError:
            pass
        except Exception as e:
            self.logger.error(f"AI 语音生成失败: {e}")

    async def on_c2c_message_create(self, message: Any):
        """处理 QQ 单聊消息 (C2C_MESSAGE_CREATE)"""
        self.logger.info(f"[EVENT] on_c2c_message_create triggered")
        await self.dispatcher.route(message, SCENE_C2C)

    def _try_get_nickname(self, message) -> str:
        """从事件 author 提取昵称。

        按官方文档 User 对象字段，昵称字段为 ``username``（用户昵称）。
        群聊/单聊事件体均携带 ``author`` 对象：群聊用 member_openid、
        单聊用 user_openid 标识用户，两者都带 username。保留
        member_name/user_name 仅为旧版/兼容兜底。author 可能为 None
        （如部分系统事件）。
        """
        author = getattr(message, "author", None)
        if author is None:
            return ""
        for key in ("username", "member_name", "user_name"):
            try:
                value = getattr(author, key)
            except AttributeError:
                continue
            if value:
                return str(value)
        return ""

    async def on_group_at_message_create(self, message: Any):
        """处理 QQ 群聊@机器人消息 (GROUP_AT_MESSAGE_CREATE)"""
        self.logger.info(f"[EVENT] on_group_at_message_create triggered")
        await self.dispatcher.route(message, SCENE_GROUP_AT)

    async def on_group_message_create(self, message: Any):
        """处理群聊全量消息 (GROUP_MESSAGE_CREATE)"""
        self.logger.info(f"[EVENT] on_group_message_create triggered")
        await self.dispatcher.route(message, SCENE_GROUP)

    async def on_direct_message_create(self, message: DirectMessage):
        """处理频道私信消息 (DIRECT_MESSAGE_CREATE)"""
        await self.dispatcher.route(message, SCENE_DIRECT)

    async def on_at_message_create(self, message: Message):
        """处理频道@机器人消息 (AT_MESSAGE_CREATE)"""
        self.logger.info(f"[EVENT] on_at_message_create triggered")
        await self.dispatcher.route(message, SCENE_AT)

    async def on_group_add_robot(self, group: Any):
        self.logger.info(f"机器人被添加到群: {getattr(group, 'group_openid', None) or 'unknown'}")

    async def on_group_del_robot(self, group: Any):
        self.logger.info(f"机器人被移出群: {getattr(group, 'group_openid', None) or 'unknown'}")

    async def on_group_msg_reject(self, group: Any):
        self.logger.info(f"群消息被拒绝: {getattr(group, 'group_openid', None) or 'unknown'}")

    async def on_group_msg_receive(self, group: Any):
        self.logger.info(f"群消息接收恢复: {getattr(group, 'group_openid', None) or 'unknown'}")

    async def on_friend_add(self, user: Any):
        self.logger.info(f"好友添加: {getattr(user, 'user_openid', None) or 'unknown'}")

    async def on_friend_del(self, user: Any):
        self.logger.info(f"好友删除: {getattr(user, 'user_openid', None) or 'unknown'}")

    def _get_status_text(self) -> str:
        try:
            from qqbot_openapi.psutil_compat import virtual_memory
            memory = virtual_memory()
            memory_text = f"{memory.percent}%"
        except Exception:
            memory_text = "N/A"

        return f"""## 📊 {self.bot_name} 状态

### 系统信息
- **内存**: {memory_text}

### AI 配置
- **AI 模型**: {self.context.EnableNetwork}
- **版本**: {self.version_name}"""
