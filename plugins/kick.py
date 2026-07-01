# -*- coding: utf-8 -*-
"""
Kick 直播状态查询插件 - 适配 QQ 开放平台
支持查询 Kick 主播直播状态、自动开播提醒
"""

import os
import json
import asyncio
import threading
import time
import urllib.request
import urllib.error

TRIGGHT_KEYWORD = "kick"
HELP_MESSAGE = "kick <主播名> -> 查询 Kick 主播直播状态 | kick help 查看更多"

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kick_config.json")
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kick.log")

# 全局变量
_monitor_thread = None
_monitor_running = False
_client = None
_notified: set = set()
_send_queue = None  # asyncio.Queue, 在 on_message 时初始化
_sender_task = None


def _load_config() -> dict:
    """加载配置"""
    default_config = {
        "streamers": [],
        "notify_groups": [],
        "check_interval": 60
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Kick插件] 加载配置失败: {e}")
    
    return default_config


def _save_config(config: dict) -> bool:
    """保存配置"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"[Kick插件] 保存配置失败: {e}")
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


def _check_live_sync(channel: str) -> tuple:
    """同步检查主播直播状态"""
    url = f"https://api.kick.com/private/v1/channels/{channel}/livestream"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode())
            livestream = body.get("data", {}).get("livestream")
            if livestream and livestream.get("id"):
                return (False, livestream)
            return (False, None)
    except Exception as e:
        print(f"[Kick插件] 检查 {channel} 失败: {e}")
        return (True, None)


async def _check_live(channel: str) -> tuple:
    """异步检查主播直播状态"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _check_live_sync, channel)


def _format_live_info(channel: str, live_info: dict) -> str:
    """格式化直播信息"""
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


def _send_message_sync(group_openid: str, content: str):
    """将消息放入队列，由主 loop 的 sender task 发送"""
    if not _client or not _send_queue:
        return
    try:
        _send_queue.put_nowait((group_openid, content))
    except Exception:
        pass


async def _sender_loop():
    """主 loop 后台 task：从队列取消息并发送"""
    while True:
        try:
            group_openid, content = await _send_queue.get()
            try:
                await _client.api.post_group_message(
                    group_openid=group_openid,
                    msg_type=0,
                    content=content,
                    msg_seq=str(int(time.time() * 1000000) % 100000000),
                )
                print(f"[Kick插件] 已发送到群 {group_openid}")
            except Exception as e:
                print(f"[Kick插件] 发送到群 {group_openid} 失败: {e}")
            finally:
                _send_queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[Kick插件] sender 异常: {e}")
            await asyncio.sleep(1)


def _broadcast_to_groups(notify_groups: list, content: str):
    """向所有通知群发送消息"""
    for group_id in notify_groups:
        _send_message_sync(group_id, content)
        time.sleep(0.3)


def _check_all_streamers(streamers: list) -> dict:
    """并发检查所有主播状态，返回 {channel: livestream_or_None}"""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = {}
    if not streamers:
        return results

    with ThreadPoolExecutor(max_workers=min(len(streamers), 8)) as pool:
        futures = {pool.submit(_check_live_sync, ch): ch for ch in streamers}
        for future in as_completed(futures):
            channel = futures[future]
            try:
                is_error, live_info = future.result()
                results[channel] = None if is_error else live_info
            except Exception:
                results[channel] = None

    return results


class _ConfigCache:
    """配置缓存，仅文件变化时重新加载"""

    def __init__(self):
        self._data = None
        self._mtime = 0.0

    def get(self) -> dict:
        try:
            mtime = os.path.getmtime(CONFIG_FILE)
        except OSError:
            return self._default()

        if self._data is not None and mtime == self._mtime:
            return self._data

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                self._data = json.load(f)
                self._mtime = mtime
                return self._data
        except Exception:
            return self._default()

    @staticmethod
    def _default() -> dict:
        return {"streamers": [], "notify_groups": [], "check_interval": 60}


_config_cache = _ConfigCache()


def _monitor_loop():
    """监控主循环"""
    global _notified, _monitor_running

    print("[Kick插件] 监控线程启动")

    while _monitor_running:
        try:
            config = _config_cache.get()
            interval = config.get("check_interval", 60)
            notify_groups = config.get("notify_groups", [])
            streamers = [s.lower() for s in config.get("streamers", [])]

            if not streamers or not notify_groups:
                time.sleep(interval)
                continue

            live_results = _check_all_streamers(streamers)

            for channel in streamers:
                live_info = live_results.get(channel)

                if live_info:
                    if channel not in _notified:
                        title = live_info.get("metadata", {}).get("title", "未知")
                        viewers = live_info.get("viewers_count", 0)
                        message = _format_live_info(channel, live_info)
                        _broadcast_to_groups(notify_groups, message)
                        _notified.add(channel)
                        _write_log("开播", f"{channel} | 标题={title} 观众={viewers}")
                        print(f"[Kick插件] {channel} 开播了")
                else:
                    if channel in _notified:
                        message = f"⚫ {channel} 下播了\n链接: https://kick.com/{channel}"
                        _broadcast_to_groups(notify_groups, message)
                        _notified.discard(channel)
                        _write_log("下播", channel)
                        print(f"[Kick插件] {channel} 下播了")

            stale = _notified - set(streamers)
            for ch in stale:
                _notified.discard(ch)

            time.sleep(interval)
        except Exception as e:
            print(f"[Kick插件] 监控循环错误: {e}")
            time.sleep(30)

    print("[Kick插件] 监控线程停止")


def _start_monitor():
    """启动监控"""
    global _monitor_thread, _monitor_running
    
    if _monitor_thread and _monitor_thread.is_alive():
        return False
    
    _monitor_running = True
    _monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
    _monitor_thread.start()
    return True


def _stop_monitor():
    """停止监控"""
    global _monitor_running
    _monitor_running = False
    return True


async def on_message(event, actions, **kwargs):
    """插件主入口"""
    global _client, _send_queue, _sender_task
    
    # 保存 client 引用，初始化发送队列和 sender task
    if hasattr(actions, '_client'):
        _client = actions._client
        if _send_queue is None:
            _send_queue = asyncio.Queue()
        if _sender_task is None or _sender_task.done():
            _sender_task = asyncio.create_task(_sender_loop())
    
    content = event.message if hasattr(event, 'message') else ""
    
    # 解析命令
    parts = content.split(maxsplit=2)
    if len(parts) < 2 or parts[0].lower() != "kick":
        return False
    
    cmd = parts[1].lower() if len(parts) > 1 else ""
    args = parts[2] if len(parts) > 2 else ""
    
    config = _load_config()
    
    # 帮助信息
    if cmd == "help" or cmd == "帮助":
        help_text = (
            "📺 Kick 直播提醒命令:\n"
            "• kick <主播名> — 查询主播直播状态\n"
            "• kick add <主播名> — 添加监控主播\n"
            "• kick del <主播名> — 删除监控主播\n"
            "• kick list — 查看监控列表\n"
            "• kick check — 检查所有主播状态\n"
            "• kick group add <群号> — 添加通知群聊\n"
            "• kick group del <群号> — 删除通知群聊\n"
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
                    "group", "start", "stop", "status", "interval", "help", "帮助"):
        channel = cmd.lower()
        user_id = getattr(event, 'user_id', '')
        group_id = getattr(event, 'group_id', '')
        await actions.send(content=f"正在查询 {channel} 的直播状态...")
        
        is_error, live_info = await _check_live(channel)
        
        if is_error:
            _write_log("查询", f"{channel} 查询失败", user_id, group_id)
            await actions.send(content=f"❌ 查询 {channel} 失败，请稍后再试")
        elif live_info:
            title = live_info.get("metadata", {}).get("title", "未知")
            viewers = live_info.get("viewers_count", 0)
            _write_log("查询", f"{channel} 直播中 | 标题={title} 观众={viewers}", user_id, group_id)
            await actions.send(content=_format_live_info(channel, live_info))
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
        user_id = getattr(event, 'user_id', '')
        group_id = getattr(event, 'group_id', '')
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
        user_id = getattr(event, 'user_id', '')
        group_id = getattr(event, 'group_id', '')
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
        
        if not streamers:
            await actions.send(content="📺 监控列表为空\n使用 kick add <主播名> 添加监控")
            return True
        
        text_parts = ["📺 监控列表:"]
        for i, s in enumerate(streamers, 1):
            status = "🔴 直播中" if s.lower() in _notified else "⚫ 未开播"
            text_parts.append(f"{i}. {s} {status}")
        
        text_parts.append(f"\n📢 通知群聊: {len(notify_groups)} 个")
        text_parts.append(f"⏱️ 检查间隔: {config.get('check_interval', 60)} 秒")
        text_parts.append(f"🔄 监控状态: {'运行中' if _monitor_running else '已停止'}")
        
        await actions.send(content="\n".join(text_parts))
        return True
    
    # 检查所有主播状态
    if cmd == "check":
        streamers = config.get("streamers", [])
        
        if not streamers:
            await actions.send(content="📺 监控列表为空，无法检查")
            return True
        
        await actions.send(content=f"正在检查 {len(streamers)} 个主播的状态...")
        
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
            
            await asyncio.sleep(0.3)
        
        text_parts = [f"📊 检查结果 ({live_count}/{len(streamers)} 直播中):"]
        text_parts.extend(results)
        
        await actions.send(content="\n".join(text_parts))
        return True
    
    # 管理通知群聊
    if cmd == "group":
        subcmd = args.split(maxsplit=1)[0].lower() if args else ""
        
        # 自动获取当前群的 group_openid
        current_group = getattr(event, 'group_id', None)
        user_id = getattr(event, 'user_id', '')
        
        if subcmd == "add":
            group_id = current_group if current_group else (args.split(maxsplit=1)[1].strip() if len(args.split(maxsplit=1)) > 1 else "")
            
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
            # 删除时支持删除当前群或指定群
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
    
    # 启动监控
    if cmd == "start":
        user_id = getattr(event, 'user_id', '')
        group_id = getattr(event, 'group_id', '')
        if not config.get("streamers"):
            await actions.send(content="⚠️ 监控列表为空，请先添加主播")
            return True
        
        if not config.get("notify_groups"):
            await actions.send(content="⚠️ 未设置通知群聊，请先添加")
            return True
        
        if _start_monitor():
            _write_log("启动监控", f"间隔={config.get('check_interval', 60)}s", user_id, group_id)
            await actions.send(content=f"✅ 自动监控已启动\n检查间隔: {config.get('check_interval', 60)} 秒")
        else:
            await actions.send(content="⚠️ 监控已在运行中")
        return True
    
    # 停止监控
    if cmd == "stop":
        user_id = getattr(event, 'user_id', '')
        group_id = getattr(event, 'group_id', '')
        if _monitor_running:
            _stop_monitor()
            _write_log("停止监控", "", user_id, group_id)
            await actions.send(content="✅ 自动监控已停止")
        else:
            await actions.send(content="⚠️ 监控未在运行")
        return True
    
    # 查看状态
    if cmd == "status":
        status_text = (
            f"📊 Kick 监控状态:\n"
            f"• 运行状态: {'🟢 运行中' if _monitor_running else '🔴 已停止'}\n"
            f"• 监控主播: {len(config.get('streamers', []))} 个\n"
            f"• 直播中: {len(_notified)} 个\n"
            f"• 通知群聊: {len(config.get('notify_groups', []))} 个\n"
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


def _auto_start():
    """自动启动监控"""
    config = _load_config()
    if config.get("streamers") and config.get("notify_groups"):
        print(f"[Kick插件] 检测到配置，自动启动监控")
        _start_monitor()

# 延迟启动
threading.Timer(5.0, _auto_start).start()
