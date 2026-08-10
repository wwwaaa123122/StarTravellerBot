# -*- coding: utf-8 -*-

from __future__ import annotations

from datetime import timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

_scheduler: AsyncIOScheduler | None = None
_client = None


def _default_timezone():
    try:
        from tzlocal import get_localzone
        return get_localzone()
    except Exception:
        return timezone.utc


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone=_default_timezone())
    return _scheduler


def set_client(client) -> None:
    global _client
    _client = client


def get_client():
    return _client


def shutdown():
    global _scheduler
    if _scheduler:
        try:
            _scheduler.shutdown(wait=False)
        except Exception:
            pass
        _scheduler = None
