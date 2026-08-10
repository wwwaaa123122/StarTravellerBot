# -*- coding: utf-8 -*-

import time
from collections import deque
from typing import Deque, Dict


class MessageDedup:

    def __init__(self, window: float = 60.0, max_items: int = 500):
        self.window = window
        self.max_items = max_items
        self._seen: Dict[str, float] = {}
        self._order: Deque[str] = deque()

    def is_duplicate(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window

        while self._order and self._seen.get(self._order[0], 0) < cutoff:
            self._seen.pop(self._order.popleft(), None)

        if key in self._seen:
            return True
        self._seen[key] = now
        self._order.append(key)
        if len(self._seen) > self.max_items:
            self._seen.pop(self._order.popleft(), None)
        return False
