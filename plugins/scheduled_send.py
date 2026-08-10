# -*- coding: utf-8 -*-

import os
import json
from datetime import datetime, timezone, timedelta

from apscheduler.triggers.cron import CronTrigger

from Tools.scheduler import get_client

BJT = timezone(timedelta(hours=8))

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
    config = getattr(client, 'config', {}) or {}
    cfg = config.get("scheduled_send", {})
    if not cfg.get("enabled", True):
        return
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
    send_time = os.environ.get("STAR_SCHEDULED_SEND_TIME", "06:00")
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
    event = ctx.event
    actions = ctx.actions
    kwargs = ctx.kwargs
    order = kwargs.get("order", "")
    user_id = str(getattr(event, "user_id", ""))
    config = kwargs.get("config", {})

    cfg = config.get("scheduled_send", {})
    admin_user = cfg.get("admin_user", "")

    if not admin_user or user_id != admin_user:
        return False
    notify_groups = cfg.get("notify_groups", [])
    default_content = cfg.get("default_content", "早生蚝")

    if not notify_groups:
        await actions.send(content="未配置通知群聊 (scheduled_send.notify_groups)")
        return True

    content = default_content
    rest = order[len("群发"):].strip()
    if rest:
        content = rest

    await actions.send(content=f"正在向 {len(notify_groups)} 个群发送: {content}")

    client = kwargs.get("client")
    if client:
        await _send_to_groups(client, content, notify_groups)

    return True
