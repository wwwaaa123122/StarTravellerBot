# -*- coding: utf-8 -*-
"""AI 调用限流：滑动窗口，按用户/全局维度限制每分钟请求数。"""

import time
from collections import defaultdict, deque
from typing import Deque, Dict, Tuple

DEFAULT_USER_RPM = 10
DEFAULT_GLOBAL_RPM = 60


class RateLimiter:
    """滑动窗口限流器；check 返回 (是否放行, 剩余可调用次数)。"""

    def __init__(self, user_rpm: int = DEFAULT_USER_RPM, global_rpm: int = DEFAULT_GLOBAL_RPM):
        self.user_rpm = max(user_rpm, 1)
        self.global_rpm = max(global_rpm, 1)
        self._user_hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._global_hits: Deque[float] = deque()

    @staticmethod
    def _prune(hits: Deque[float], window: float = 60.0):
        cutoff = time.monotonic() - window
        while hits and hits[0] < cutoff:
            hits.popleft()

    def check(self, user_id: str = "") -> Tuple[bool, int]:
        """检查 user_id 的请求是否放行；返回 (是否放行, 剩余额度)。"""
        now = time.monotonic()
        self._prune(self._global_hits)
        if len(self._global_hits) >= self.global_rpm:
            return False, self.global_rpm - len(self._global_hits)

        if user_id:
            hits = self._user_hits[user_id]
            self._prune(hits)
            if len(hits) >= self.user_rpm:
                return False, self.user_rpm - len(hits)
        return True, 0

    def record(self, user_id: str = ""):
        """记录一次已放行的调用。"""
        now = time.monotonic()
        self._global_hits.append(now)
        if user_id:
            self._user_hits[user_id].append(now)
