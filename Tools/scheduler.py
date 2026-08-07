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

from apscheduler.schedulers.asyncio import AsyncIOScheduler

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """
    获取全局 AsyncIOScheduler 单例

    首次调用时创建，后续调用返回同一实例。
    可通过 scheduler._client 访问机器人客户端引用（由 client.py 设置）。
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


def shutdown():
    """安全关闭调度器（不等待正在执行的任务）"""
    global _scheduler
    if _scheduler:
        try:
            _scheduler.shutdown(wait=False)
        except Exception:
            pass
        _scheduler = None