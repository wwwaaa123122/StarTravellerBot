# -*- coding: utf-8 -*-
"""
集中式异步任务调度器 (基于 APScheduler)
统一管理所有插件定时任务，替代 while True + sleep 模式

用法:
    from Tools.scheduler import get_scheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger

    scheduler = get_scheduler()
    scheduler.add_job(my_async_func, CronTrigger(hour=6, minute=0))
    scheduler.start()
"""

from __future__ import annotations

from datetime import timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

_scheduler: AsyncIOScheduler | None = None
_client = None


def _default_timezone():
    """本地时区；Termux 缺 tzdata 时 zoneinfo 解析失败，回退 UTC。"""
    try:
        from tzlocal import get_localzone
        return get_localzone()
    except Exception:
        return timezone.utc


def get_scheduler() -> AsyncIOScheduler:
    """
    获取全局 AsyncIOScheduler 单例

    首次调用时创建，后续调用返回同一实例。
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone=_default_timezone())
    return _scheduler


def set_client(client) -> None:
    """注入机器人客户端引用，供定时任务插件访问（替代 scheduler._client 属性注入）。"""
    global _client
    _client = client


def get_client():
    """获取机器人客户端引用（由 main.py/client.py 注入）。"""
    return _client


def shutdown():
    """安全关闭调度器（不等待正在执行的任务）"""
    global _scheduler
    if _scheduler:
        try:
            _scheduler.shutdown(wait=False)
        except Exception:
            pass
        _scheduler = None
