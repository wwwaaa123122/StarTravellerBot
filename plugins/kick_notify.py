# -*- coding: utf-8 -*-
"""
Kick 开播提醒 - QQ 开放平台插件
监控 Kick 主播开播状态，通过 botpy API 发送通知
"""

import json
import asyncio
import logging
import urllib.request
import urllib.error

_logger = logging.getLogger("KickNotify")

HELP_MESSAGE = "Kick 开播监控 (channel: xctraveller, 间隔60秒)"

# 已通知过的主播集合 (避免重复通知)
_notified: set[str] = set()


def _check_live(channel: str) -> tuple[bool, dict | None]:
    """检查 Kick 主播是否在播。"""
    url = f"https://api.kick.com/private/v1/channels/{channel}/livestream"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode())
            livestream = body.get("data", {}).get("livestream")
            if livestream and livestream.get("id"):
                return (False, livestream)
            return (False, None)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError) as e:
        _logger.warning(f"检查 {channel} 失败: {e}")
        return (True, None)


def _format_live_msg(channel: str, live_info: dict) -> str:
    """格式化开播通知消息"""
    meta = live_info.get("metadata", {})
    title = meta.get("title", "未知标题")
    category = meta.get("category", {}).get("name", "未知分类")
    viewers = live_info.get("viewers_count", 0)
    url = f"https://kick.com/{channel}"
    return (
        f"## 🔴 {channel} 开播了!\n\n"
        f"- **标题**: {title}\n"
        f"- **分类**: {category}\n"
        f"- **观众**: {viewers}\n"
        f"- **链接**: {url}"
    )


def _format_offline_msg(channel: str) -> str:
    """格式化下播通知消息"""
    url = f"https://kick.com/{channel}"
    return f"## ⚫ {channel} 下播了\n\n- **链接**: {url}"


async def _send_notification(client, message: str, notify_groups: list, notify_users: list):
    """通过 botpy API 发送通知到指定群和用户"""
    for group_openid in notify_groups:
        try:
            await client.api.post_group_message(
                group_openid=group_openid,
                msg_type=2,
                markdown={"content": message},
                msg_id="",
            )
            client.logger.info(f"[kick_notify] 已发送群通知 {group_openid}")
        except Exception as e:
            client.logger.error(f"[kick_notify] 群 {group_openid} 发送失败: {e}")

    for user_openid in notify_users:
        try:
            await client.api.post_c2c_message(
                openid=user_openid,
                msg_type=2,
                markdown={"content": message},
                msg_id="",
            )
            client.logger.info(f"[kick_notify] 已发送私聊通知 {user_openid}")
        except Exception as e:
            client.logger.error(f"[kick_notify] 私聊 {user_openid} 发送失败: {e}")


async def background_tasks(client):
    """Kick 开播监控后台循环"""
    # 等待 bot 完全就绪
    await asyncio.sleep(3)

    config = getattr(client, 'config', {}) or {}
    cfg = config.get("kick_notify", {})
    channel = cfg.get("channel", "xctraveller")
    interval = cfg.get("check_interval", 60)
    notify_groups = cfg.get("notify_groups", [])
    notify_users = cfg.get("notify_users", [])

    if not notify_groups and not notify_users:
        client.logger.warning("[kick_notify] 未配置通知目标 (notify_groups/notify_users)，不会发送任何消息")

    client.logger.info(f"[kick_notify] 开始监控 {channel}，间隔 {interval}s")

    # 初始化状态，不发送通知
    is_error, live_info = _check_live(channel)
    if not is_error and live_info:
        _notified.add(channel.lower())
        client.logger.info(f"[kick_notify] {channel}: 已开播 (初始化记录，不通知)")
    else:
        client.logger.info(f"[kick_notify] {channel}: 未开播")

    while True:
        await asyncio.sleep(interval)

        is_error, live_info = _check_live(channel)
        if is_error:
            client.logger.warning(f"[kick_notify] 查询 {channel} 失败，跳过本轮")
            continue

        if live_info:
            if channel.lower() not in _notified:
                client.logger.info(f"[kick_notify] {channel} 开播!")
                msg = _format_live_msg(channel, live_info)
                await _send_notification(client, msg, notify_groups, notify_users)
                _notified.add(channel.lower())
        else:
            if channel.lower() in _notified:
                _notified.discard(channel.lower())
                client.logger.info(f"[kick_notify] {channel} 下播")
                msg = _format_offline_msg(channel)
                await _send_notification(client, msg, notify_groups, notify_users)

