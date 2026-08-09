# -*- coding: utf-8 -*-
"""
Kick 直播监控插件 - 统一版
- 多主播开播/下播提醒（APScheduler IntervalTrigger）
- 支持群聊和私聊通知（Markdown）
- 完整的命令系统（add/del/list/check/start/stop/status/interval/group/user）
"""

import os
import json
import time
import logging
from datetime import timezone, timedelta
from typing import Optional

import httpx
from apscheduler.triggers.interval import IntervalTrigger

from Tools.scheduler import get_client

_logger = logging.getLogger("KickPlugin")

# 北京时间 (UTC+8)；显式传入避免 Termux 缺 tzdata 时 IntervalTrigger 的 get_localzone 失败
BJT = timezone(timedelta(hours=8))

# 配置文件路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(BASE_DIR, "plugins", "kick_config.json")
LOG_FILE = os.path.join(BASE_DIR, "data", "kick.log")

# 已通知过的主播集合（避免重复通知）
_notified: set[str] = set()
# 调度器引用（用于动态调整间隔）
_scheduler = None
# 当前检查间隔缓存（用于 reschedule 时判断）
_current_interval = 0


def _load_config() -> dict:
    """加载配置"""
    default_config = {
        "streamers": [],
        "notify_groups": [],
        "notify_users": [],
        "check_interval": 60,
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                # 兼容旧配置（无 notify_users 字段）
                cfg.setdefault("notify_users", [])
                return cfg
        except Exception as e:
            _logger.error(f"加载配置失败: {e}")
    return default_config


def _save_config(config: dict) -> bool:
    """保存配置"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        _logger.error(f"保存配置失败: {e}")
        return False


def _write_log(action: str, detail: str, user_id: str = "", group_id: str = ""):
    """写入操作日志"""
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {action} | {detail}"
        if user_id:
            line += f" | user={user_id}"
        if group_id:
            line += f" | group={group_id}"
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


async def _check_live(channel: str) -> tuple[bool, Optional[dict]]:
    """异步检查 Kick 主播直播状态，返回 (is_error, livestream_dict_or_None)"""
    url = f"https://api.kick.com/private/v1/channels/{channel}/livestream"
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as session:
            resp = await session.get(url, headers=headers)
            resp.raise_for_status()
            body = resp.json()
            livestream = body.get("data", {}).get("livestream")
            if livestream and livestream.get("id"):
                return (False, livestream)
            return (False, None)
    except Exception as e:
        _logger.warning(f"检查 {channel} 失败: {e}")
        return (True, None)


def _format_live_msg(channel: str, live_info: dict) -> str:
    """格式化开播通知（Markdown）"""
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
    """格式化下播通知（Markdown）"""
    url = f"https://kick.com/{channel}"
    return f"## ⚫ {channel} 下播了\n\n- **链接**: {url}"


def _format_live_text(channel: str, live_info: dict) -> str:
    """格式化直播信息（纯文本，用于命令查询）"""
    title = live_info.get("metadata", {}).get("title", "未知")
    category = live_info.get("metadata", {}).get("category", {}).get("name", "未知")
    viewers = live_info.get("viewers_count", 0)
    return (
        f"🔴 {channel} 开播了!\n"
        f"标题: {title}\n"
        f"分类: {category}\n"
        f"观众: {viewers}\n"
        f"链接: https://kick.com/{channel}"
    )


async def _send_notification(client, message: str, notify_groups: list, notify_users: list):
    """发送通知到群聊和私聊"""
    for group_openid in notify_groups:
        try:
            await client.api.post_group_message(
                group_openid=group_openid,
                msg_type=2,
                markdown={"content": message},
                msg_id="",
            )
            client.logger.info(f"[kick] 已发送群通知 {group_openid}")
        except Exception as e:
            client.logger.error(f"[kick] 群 {group_openid} 发送失败: {e}")

    for user_openid in notify_users:
        try:
            await client.api.post_c2c_message(
                openid=user_openid,
                msg_type=2,
                markdown={"content": message},
                msg_id="",
            )
            client.logger.info(f"[kick] 已发送私聊通知 {user_openid}")
        except Exception as e:
            client.logger.error(f"[kick] 私聊 {user_openid} 发送失败: {e}")


async def _do_monitor_check(client):
    """执行一次监控检查"""
    global _notified

    config = _load_config()
    streamers = [s.lower() for s in config.get("streamers", [])]
    notify_groups = config.get("notify_groups", [])
    notify_users = config.get("notify_users", [])

    if not streamers:
        return

    for channel in streamers:
        is_error, live_info = await _check_live(channel)
        if is_error:
            continue

        if live_info:
            if channel not in _notified:
                title = live_info.get("metadata", {}).get("title", "未知")
                viewers = live_info.get("viewers_count", 0)
                msg = _format_live_msg(channel, live_info)
                await _send_notification(client, msg, notify_groups, notify_users)
                _notified.add(channel)
                _write_log("开播", f"{channel} | 标题={title} 观众={viewers}")
                _logger.info(f"[kick] {channel} 开播了")
        else:
            if channel in _notified:
                msg = _format_offline_msg(channel)
                await _send_notification(client, msg, notify_groups, notify_users)
                _notified.discard(channel)
                _write_log("下播", channel)
                _logger.info(f"[kick] {channel} 下播了")

    # 清理已移除主播的通知状态
    stale = _notified - set(streamers)
    for ch in stale:
        _notified.discard(ch)


def _init_check(client):
    """初始化检查：记录当前状态，不发送通知"""
    import asyncio

    async def _do():
        config = _load_config()
        streamers = [s.lower() for s in config.get("streamers", [])]
        for channel in streamers:
            is_error, live_info = await _check_live(channel)
            if is_error:
                continue
            if live_info:
                _notified.add(channel)
                _logger.info(f"[kick] {channel}: 已开播 (初始化记录，不通知)")
            else:
                _logger.info(f"[kick] {channel}: 未开播")

    asyncio.create_task(_do())


async def _monitor_job():
    """APScheduler 定时任务：执行监控检查并动态调整间隔"""
    global _scheduler

    client = get_client()
    if not client:
        return

    await _do_monitor_check(client)

    # 动态调整间隔（如果配置变更）
    config = _load_config()
    new_interval = config.get("check_interval", 60)
    global _current_interval
    if new_interval != _current_interval and _scheduler:
        _current_interval = new_interval
        _scheduler.reschedule_job(
            "kick_monitor",
            trigger=IntervalTrigger(seconds=new_interval, timezone=BJT),
        )
        _logger.info(f"[kick] 检查间隔已更新为 {new_interval}s")


def register_scheduled_jobs(scheduler):
    """注册定时任务到 APScheduler"""
    global _scheduler, _current_interval

    _scheduler = scheduler
    config = _load_config()
    _current_interval = config.get("check_interval", 60)

    # 初始化检查：启动后 5 秒执行一次，记录当前状态但不通知
    scheduler.add_job(
        lambda: _init_check(get_client()),
        trigger=None,
        id="kick_init_check",
        name="Kick 初始化状态检查",
        replace_existing=True,
        next_run_time=None,  # 下面手动设置
    )

    # 监控任务
    scheduler.add_job(
        _monitor_job,
        IntervalTrigger(seconds=_current_interval, timezone=BJT),
        id="kick_monitor",
        name="Kick 直播监控",
        replace_existing=True,
    )

    _logger.info(f"[kick] 监控任务已注册，间隔 {_current_interval}s")


# ==================== 插件接口 ====================

TRIGGER_KEYWORD = "kick"
HELP_MESSAGE = "kick <主播名> -> 查询 Kick 主播直播状态 | kick help 查看更多"


async def on_message(ctx):
    """插件命令处理入口"""
    event = ctx.event
    actions = ctx.actions
    kwargs = ctx.kwargs
    global _scheduler, _current_interval
    content = event.message if hasattr(event, 'message') else ""

    parts = content.split(maxsplit=2)
    if len(parts) < 2 or parts[0].lower() != "kick":
        return False

    cmd = parts[1].lower() if len(parts) > 1 else ""
    args = parts[2] if len(parts) > 2 else ""

    config = _load_config()
    client = kwargs.get("client")

    # 帮助信息
    if cmd in ("help", "帮助"):
        help_text = (
            "📺 Kick 直播提醒命令:\n"
            "• kick <主播名> — 查询主播直播状态\n"
            "• kick add <主播名> — 添加监控主播\n"
            "• kick del <主播名> — 删除监控主播\n"
            "• kick list — 查看监控列表\n"
            "• kick check — 检查所有主播状态\n"
            "• kick group add — 添加当前群为通知群\n"
            "• kick group del — 删除当前群\n"
            "• kick user add <用户ID> — 添加通知用户\n"
            "• kick user del <用户ID> — 删除通知用户\n"
            "• kick start — 启动自动监控\n"
            "• kick stop — 停止自动监控\n"
            "• kick status — 查看监控状态\n"
            "• kick interval <秒数> — 设置检查间隔\n"
            "• kick help — 显示帮助"
        )
        await actions.send(content=help_text)
        return True

    # 查询单个主播
    if cmd not in ("add", "del", "delete", "remove", "list", "ls", "check",
                    "group", "user", "start", "stop", "status", "interval", "help", "帮助"):
        channel = cmd.lower()
        user_id = str(getattr(event, 'user_id', ''))
        group_id = str(getattr(event, 'group_id', ''))
        await actions.send(content=f"正在查询 {channel} 的直播状态...")

        is_error, live_info = await _check_live(channel)

        if is_error:
            _write_log("查询", f"{channel} 查询失败", user_id, group_id)
            await actions.send(content=f"❌ 查询 {channel} 失败，请稍后再试")
        elif live_info:
            title = live_info.get("metadata", {}).get("title", "未知")
            viewers = live_info.get("viewers_count", 0)
            _write_log("查询", f"{channel} 直播中 | 标题={title} 观众={viewers}", user_id, group_id)
            await actions.send(content=_format_live_text(channel, live_info))
        else:
            _write_log("查询", f"{channel} 未在直播", user_id, group_id)
            await actions.send(content=f"⚫ {channel} 未在直播\n链接: https://kick.com/{channel}")
        return True

    # 添加监控主播
    if cmd == "add":
        if not args:
            await actions.send(content="请指定主播名，如: kick add xctraveller")
            return True

        channel = args.strip().lower()
        user_id = str(getattr(event, 'user_id', ''))
        group_id = str(getattr(event, 'group_id', ''))
        if channel not in [s.lower() for s in config["streamers"]]:
            config["streamers"].append(channel)
            if _save_config(config):
                _write_log("添加监控", channel, user_id, group_id)
                await actions.send(content=f"✅ 已添加监控: {channel}")
            else:
                await actions.send(content="❌ 保存配置失败")
        else:
            await actions.send(content=f"⚠️ {channel} 已在监控列表中")
        return True

    # 删除监控主播
    if cmd in ("del", "delete", "remove"):
        if not args:
            await actions.send(content="请指定主播名，如: kick del xctraveller")
            return True

        channel = args.strip().lower()
        user_id = str(getattr(event, 'user_id', ''))
        group_id = str(getattr(event, 'group_id', ''))
        original_len = len(config["streamers"])
        config["streamers"] = [s for s in config["streamers"] if s.lower() != channel]

        if len(config["streamers"]) < original_len:
            if _save_config(config):
                _notified.discard(channel)
                _write_log("删除监控", channel, user_id, group_id)
                await actions.send(content=f"✅ 已删除监控: {channel}")
            else:
                await actions.send(content="❌ 保存配置失败")
        else:
            await actions.send(content=f"⚠️ {channel} 不在监控列表中")
        return True

    # 查看监控列表
    if cmd in ("list", "ls"):
        streamers = config.get("streamers", [])
        notify_groups = config.get("notify_groups", [])
        notify_users = config.get("notify_users", [])

        if not streamers:
            await actions.send(content="📺 监控列表为空\n使用 kick add <主播名> 添加监控")
            return True

        text_parts = ["📺 监控列表:"]
        for i, s in enumerate(streamers, 1):
            status = "🔴 直播中" if s.lower() in _notified else "⚫ 未开播"
            text_parts.append(f"{i}. {s} {status}")

        text_parts.append(f"\n📢 通知群聊: {len(notify_groups)} 个")
        text_parts.append(f"👤 通知用户: {len(notify_users)} 个")
        text_parts.append(f"⏱️ 检查间隔: {config.get('check_interval', 60)} 秒")

        # 监控状态
        job = _scheduler.get_job("kick_monitor") if _scheduler else None
        running = job is not None
        text_parts.append(f"🔄 监控状态: {'运行中' if running else '已停止'}")
        await actions.send(content="\n".join(text_parts))
        return True

    # 检查所有主播状态
    if cmd == "check":
        streamers = config.get("streamers", [])

        if not streamers:
            await actions.send(content="📺 监控列表为空，无法检查")
            return True

        await actions.send(content=f"正在检查 {len(streamers)} 个主播的状态...")

        import asyncio as _asyncio
        results = []
        live_count = 0

        for channel in streamers:
            is_error, live_info = await _check_live(channel)

            if is_error:
                results.append(f"❓ {channel} - 查询失败")
            elif live_info:
                title = live_info.get("metadata", {}).get("title", "未知")
                viewers = live_info.get("viewers_count", 0)
                results.append(f"🔴 {channel} - 直播中 ({viewers}人) - {title}")
                live_count += 1
            else:
                results.append(f"⚫ {channel} - 未开播")

            await _asyncio.sleep(0.3)

        text_parts = [f"📊 检查结果 ({live_count}/{len(streamers)} 直播中):"]
        text_parts.extend(results)
        await actions.send(content="\n".join(text_parts))
        return True

    # 管理通知群聊
    if cmd == "group":
        subcmd = args.split(maxsplit=1)[0].lower() if args else ""
        current_group = str(getattr(event, 'group_id', ''))
        user_id = str(getattr(event, 'user_id', ''))

        if subcmd == "add":
            group_id = current_group or (args.split(maxsplit=1)[1].strip() if len(args.split(maxsplit=1)) > 1 else "")
            if not group_id:
                await actions.send(content="请在群聊中使用此命令，或指定群号: kick group add <群号>")
                return True
            if group_id not in config["notify_groups"]:
                config["notify_groups"].append(group_id)
                if _save_config(config):
                    _write_log("添加通知群", group_id, user_id, group_id)
                    await actions.send(content=f"✅ 已添加通知群聊: {group_id}")
                else:
                    await actions.send(content="❌ 保存配置失败")
            else:
                await actions.send(content=f"⚠️ 群 {group_id} 已在通知列表中")
        elif subcmd in ("del", "delete", "remove"):
            group_id = current_group if not args.split(maxsplit=1)[1:] else args.split(maxsplit=1)[1].strip()
            if not group_id:
                await actions.send(content="请在群聊中使用此命令，或指定群号: kick group del <群号>")
                return True
            if group_id in config["notify_groups"]:
                config["notify_groups"].remove(group_id)
                if _save_config(config):
                    _write_log("删除通知群", group_id, user_id, current_group or "")
                    await actions.send(content=f"✅ 已删除通知群聊: {group_id}")
                else:
                    await actions.send(content="❌ 保存配置失败")
            else:
                await actions.send(content=f"⚠️ 群 {group_id} 不在通知列表中")
        else:
            await actions.send(content="用法:\n• kick group add — 添加当前群\n• kick group del — 删除当前群")
        return True

    # 管理通知用户
    if cmd == "user":
        subcmd = args.split(maxsplit=1)[0].lower() if args else ""
        user_id = str(getattr(event, 'user_id', ''))

        if subcmd == "add":
            uid = args.split(maxsplit=1)[1].strip() if len(args.split(maxsplit=1)) > 1 else ""
            if not uid:
                await actions.send(content="请指定用户ID，如: kick user add <用户ID>")
                return True
            if uid not in config["notify_users"]:
                config["notify_users"].append(uid)
                if _save_config(config):
                    _write_log("添加通知用户", uid, user_id)
                    await actions.send(content=f"✅ 已添加通知用户: {uid}")
                else:
                    await actions.send(content="❌ 保存配置失败")
            else:
                await actions.send(content=f"⚠️ 用户 {uid} 已在通知列表中")
        elif subcmd in ("del", "delete", "remove"):
            uid = args.split(maxsplit=1)[1].strip() if len(args.split(maxsplit=1)) > 1 else ""
            if not uid:
                await actions.send(content="请指定用户ID，如: kick user del <用户ID>")
                return True
            if uid in config["notify_users"]:
                config["notify_users"].remove(uid)
                if _save_config(config):
                    _write_log("删除通知用户", uid, user_id)
                    await actions.send(content=f"✅ 已删除通知用户: {uid}")
                else:
                    await actions.send(content="❌ 保存配置失败")
            else:
                await actions.send(content=f"⚠️ 用户 {uid} 不在通知列表中")
        else:
            await actions.send(content="用法:\n• kick user add <用户ID> — 添加通知用户\n• kick user del <用户ID> — 删除通知用户")
        return True

    # 启动监控
    if cmd == "start":
        user_id = str(getattr(event, 'user_id', ''))
        group_id = str(getattr(event, 'group_id', ''))

        if not config.get("streamers"):
            await actions.send(content="⚠️ 监控列表为空，请先添加主播")
            return True
        if not config.get("notify_groups") and not config.get("notify_users"):
            await actions.send(content="⚠️ 未设置通知目标，请先添加通知群或用户")
            return True

        if _scheduler:
            job = _scheduler.get_job("kick_monitor")
            if job is None:
                _scheduler.add_job(
                    _monitor_job,
                    IntervalTrigger(seconds=config.get("check_interval", 60), timezone=BJT),
                    id="kick_monitor",
                    name="Kick 直播监控",
                    replace_existing=True,
                )
                _write_log("启动监控", f"间隔={config.get('check_interval', 60)}s", user_id, group_id)
                await actions.send(content=f"✅ 自动监控已启动\n检查间隔: {config.get('check_interval', 60)} 秒")
            else:
                await actions.send(content="⚠️ 监控已在运行中")
        else:
            await actions.send(content="❌ 调度器未初始化，请重启机器人")
        return True

    # 停止监控
    if cmd == "stop":
        user_id = str(getattr(event, 'user_id', ''))
        group_id = str(getattr(event, 'group_id', ''))

        if _scheduler:
            job = _scheduler.get_job("kick_monitor")
            if job:
                _scheduler.remove_job("kick_monitor")
                _write_log("停止监控", "", user_id, group_id)
                await actions.send(content="✅ 自动监控已停止")
            else:
                await actions.send(content="⚠️ 监控未在运行")
        else:
            await actions.send(content="⚠️ 监控未在运行")
        return True

    # 查看状态
    if cmd == "status":
        job = _scheduler.get_job("kick_monitor") if _scheduler else None
        running = job is not None

        status_text = (
            f"📊 Kick 监控状态:\n"
            f"• 运行状态: {'🟢 运行中' if running else '🔴 已停止'}\n"
            f"• 监控主播: {len(config.get('streamers', []))} 个\n"
            f"• 直播中: {len(_notified)} 个\n"
            f"• 通知群聊: {len(config.get('notify_groups', []))} 个\n"
            f"• 通知用户: {len(config.get('notify_users', []))} 个\n"
            f"• 检查间隔: {config.get('check_interval', 60)} 秒"
        )
        await actions.send(content=status_text)
        return True

    # 设置检查间隔
    if cmd == "interval":
        try:
            interval = int(args.strip())
            if interval < 30:
                await actions.send(content="⚠️ 检查间隔不能少于 30 秒")
            else:
                config["check_interval"] = interval
                if _save_config(config):
                    await actions.send(content=f"✅ 检查间隔已设置为 {interval} 秒")
                else:
                    await actions.send(content="❌ 保存配置失败")
        except ValueError:
            await actions.send(content="请指定有效的秒数，如: kick interval 60")
        return True

    return False
