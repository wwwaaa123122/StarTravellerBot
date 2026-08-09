# -*- coding: utf-8 -*-
"""消息发送：文本/Markdown 发送、回复、@提及剥离、Markdown 语法探测。"""

import time


class Messenger:
    """统一消息发送；client 提供 api 与 logger。"""

    def __init__(self, client):
        self.client = client
        self.logger = client.logger

    async def send_message(self, message, content=None, msg_type=0, markdown=None):
        """发送消息，自动识别消息类型（单聊/群聊）。"""
        group_openid = getattr(message, 'group_openid', None)
        try:
            if group_openid:
                kwargs = {
                    "group_openid": group_openid,
                    "msg_id": message.id,
                    "msg_seq": str(int(time.time() * 1000000) % 100000000),
                }
                api_method = self.client.api.post_group_message
                display_prefix = f"群 {group_openid}"
            else:
                kwargs = {
                    "openid": message.author.user_openid,
                    "msg_id": message.id,
                }
                api_method = self.client.api.post_c2c_message
                display_prefix = f"单聊 {message.author.user_openid}"

            if markdown:
                kwargs["msg_type"] = 2
                kwargs["markdown"] = markdown
                display_text = markdown.get("content", "")[:100]
            elif content and self.has_markdown_syntax(content):
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

    async def send_help_image(self, message, help_text: str) -> bool:
        try:
            await self.send_message(message, help_text)
            return True
        except Exception as e:
            self.logger.error(f"发送帮助消息失败: {e}")
            return False

    async def reply(self, message, content=None, markdown=None):
        """统一的回复接口，自动适配消息类型。"""
        if hasattr(message, 'reply'):
            kwargs = {"content": content}
            if markdown:
                kwargs["markdown"] = markdown
            await message.reply(**kwargs)
        else:
            await self.send_message(message, content, markdown=markdown)

    def strip_mention(self, content: str) -> str:
        robot_id = getattr(self.client.robot, 'id', None)
        if robot_id and content.startswith(f"<@!{robot_id}>"):
            return content[len(f"<@!{robot_id}>"):].strip()
        elif robot_id and content.startswith(f"<@{robot_id}>"):
            return content[len(f"<@{robot_id}>"):].strip()
        return content

    @staticmethod
    def has_markdown_syntax(text: str) -> bool:
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
