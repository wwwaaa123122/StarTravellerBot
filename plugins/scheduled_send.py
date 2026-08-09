# -*- coding: utf-8 -*-
"""
定时群发插件
- 每天早上 06:00 (北京时间) 向配置的群聊发送早间问候
- 管理员可手动触发群发：群发 或 群发 <自定义内容>
"""

import os
import json
from datetime import datetime, timezone, timedelta

from apscheduler.triggers.cron import CronTrigger

from Tools.scheduler import get_client

# 北京时间 (UTC+8)
BJT = timezone(timedelta(hours=8))

# 持久化文件，记录当天是否已发送过定时消息
_SENT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "scheduled_sent.json")
os.makedirs(os.path.dirname(_SENT_FILE), exist_ok=True)


def _load_sent() -> str:
    try:
        with open(_SENT_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("date", "")
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return ""


def _save_sent(date: str):
    with open(_SENT_FILE, "w", encoding="utf-8") as f:
        json.dump({"date": date}, f)


async def _send_to_groups(client, content: str, notify_groups: list):
    """通过 qqbot_openapi API 向所有通知群发送消息"""
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


async def _do_scheduled_send(client):
    """执行定时群发"""
    config = getattr(client, 'config', {}) or {}
    cfg = config.get("scheduled_send", {})
    default_content = cfg.get("default_content", "早生蚝")
    notify_groups = cfg.get("notify_groups", [])

    if not notify_groups:
        return

    today_str = datetime.now(BJT).strftime("%Y-%m-%d")
    if _load_sent() == today_str:
        return

    client.logger.info(f"[scheduled_send] 执行定时群发: {default_content}")
    await _send_to_groups(client, default_content, notify_groups)
    _save_sent(today_str)


def register_scheduled_jobs(scheduler):
    """注册定时群发任务到 APScheduler"""
    # 读取 send_time 配置（CronTrigger 需要静态 hour/minute）
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception:
        config = {}

    cfg = config.get("scheduled_send", {})
    send_time = cfg.get("send_time", "06:00")
    hour, minute = map(int, send_time.split(":"))

    async def wrapper():
        client = get_client()
        if client:
            await _do_scheduled_send(client)

    scheduler.add_job(
        wrapper,
        CronTrigger(hour=hour, minute=minute, timezone=BJT),
        id="scheduled_send",
        name="定时群发",
        replace_existing=True,
    )


TRIGGER_KEYWORD = "群发"
HELP_MESSAGE = "群发 <内容> - 手动向所有通知群发送消息（管理员专用）"


async def on_message(ctx):
    """处理手动群发命令：群发 <内容>"""
    event = ctx.event
    actions = ctx.actions
    kwargs = ctx.kwargs
    order = kwargs.get("order", "")
    user_id = str(getattr(event, "user_id", ""))
    config = kwargs.get("config", {})

    cfg = config.get("scheduled_send", {})
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

    client = kwargs.get("client")
    if client:
        await _send_to_groups(client, content, notify_groups)

    return True
