# -*- coding: utf-8 -*-
"""
定时群发插件
- 每天早上 06:00 (北京时间) 向配置的群聊发送早间问候
- 管理员可手动触发群发：早生蚝 或 早生蚝 <自定义内容>
"""

import os
import json
import asyncio
from datetime import datetime, timezone, timedelta

# 读取本项目 (open-qq/) 下的 config.json
_local_config = None


def _get_local_config():
    global _local_config
    if _local_config is None:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json"
        )
        with open(config_path, "r", encoding="utf-8") as f:
            _local_config = json.load(f)
    return _local_config

# 北京时间 (UTC+8)
BJT = timezone(timedelta(hours=8))

# 记录当天是否已发送过定时消息
_sent_today = False


async def _send_to_groups(client, content: str, notify_groups: list):
    """通过 botpy API 向所有通知群发送消息"""
    for group_openid in notify_groups:
        try:
            await client.api.post_group_message(
                group_openid=group_openid,
                msg_type=0,
                content=content,
                msg_id="",
            )
            client.logger.info(f"[scheduled_send] 已发送到群 {group_openid}: {content}")
        except Exception as e:
            client.logger.error(f"[scheduled_send] 群 {group_openid} 发送失败: {e}")


TRIGGHT_KEYWORD = "群发"
HELP_MESSAGE = "群发 <内容> - 手动向所有通知群发送消息（管理员专用）"


async def on_message(event, actions, **kwargs):
    """处理手动群发命令：群发 <内容>"""
    order = kwargs.get("order", "")
    user_id = str(getattr(event, "user_id", ""))

    cfg = _get_local_config().get("scheduled_send", {})
    admin_user = cfg.get("admin_user", "")

    # 仅 config 中指定的 admin_user 可触发
    if not admin_user or user_id != admin_user:
        return False
    notify_groups = cfg.get("notify_groups", [])
    default_content = cfg.get("default_content", "早生蚝")

    if not notify_groups:
        await actions.send(content="未配置通知群聊 (scheduled_send.notify_groups)")
        return True

    # 提取自定义内容，去掉 "群发" 关键字
    content = default_content
    rest = order[len("群发"):].strip()
    if rest:
        content = rest

    await actions.send(content=f"正在向 {len(notify_groups)} 个群发送: {content}")

    client = getattr(actions, "_client", None)
    if client:
        await _send_to_groups(client, content, notify_groups)

    return True


async def background_tasks(client):
    """定时群发后台任务 - 每天 06:00 发送早间问候"""
    await asyncio.sleep(3)

    cfg = _get_local_config().get("scheduled_send", {})
    send_time = cfg.get("send_time", "06:00")
    default_content = cfg.get("default_content", "早生蚝")
    notify_groups = cfg.get("notify_groups", [])

    if not notify_groups:
        client.logger.warning("[scheduled_send] notify_groups 为空，定时群发不会执行")
        return

    client.logger.info(
        f"[scheduled_send] 定时群发已启动，时间: {send_time}，内容: {default_content}"
    )

    global _sent_today
    target_hour, target_minute = map(int, send_time.split(":"))

    while True:
        now = datetime.now(BJT)

        if now.hour == target_hour and now.minute == target_minute and not _sent_today:
            client.logger.info(f"[scheduled_send] 执行定时群发: {default_content}")
            await _send_to_groups(client, default_content, notify_groups)
            _sent_today = True
        elif now.hour != target_hour or now.minute != target_minute:
            _sent_today = False

        await asyncio.sleep(30)



