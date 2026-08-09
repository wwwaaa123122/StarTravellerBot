# -*- coding: utf-8 -*-
"""AI 调用统计与费用估算：请求数 / token / 延迟 / 错误 / 预估费用。

数据持久化到 data/ai_stats.json（原子写入），供 webadmin 展示。
"""

import json
import os
import time
from typing import Optional

DEFAULT_PRICE_INPUT = 1.0   # 元 / 百万 token（输入）
DEFAULT_PRICE_OUTPUT = 2.0  # 元 / 百万 token（输出）


class CostTracker:
    """记录每次 AI 调用的 token/延迟/错误，并估算费用。"""

    def __init__(self, data_dir: str, price_input: float = DEFAULT_PRICE_INPUT,
                 price_output: float = DEFAULT_PRICE_OUTPUT, logger=None):
        self.stats_file = os.path.join(data_dir, "ai_stats.json")
        self.price_input = price_input
        self.price_output = price_output
        self.logger = logger

    def _load(self) -> dict:
        today = time.strftime("%Y-%m-%d")
        default = {
            "today": today,
            "requests": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "errors": 0,
            "latency_sum": 0.0,
            "cost": 0.0,
        }
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("today") != today:
                    data = default
                return data
        except (OSError, json.JSONDecodeError):
            pass
        return default

    def _save(self, data: dict):
        try:
            os.makedirs(os.path.dirname(self.stats_file), exist_ok=True)
            tmp = self.stats_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.stats_file)
        except OSError:
            pass

    def record(self, prompt_tokens: int = 0, completion_tokens: int = 0,
               latency: float = 0.0, error: bool = False):
        """记录一次调用（成功或失败）。"""
        try:
            data = self._load()
            data["requests"] += 1
            data["prompt_tokens"] += max(prompt_tokens, 0)
            data["completion_tokens"] += max(completion_tokens, 0)
            data["latency_sum"] += max(latency, 0.0)
            if error:
                data["errors"] += 1
            data["cost"] += (max(prompt_tokens, 0) / 1_000_000) * self.price_input
            data["cost"] += (max(completion_tokens, 0) / 1_000_000) * self.price_output
            self._save(data)
        except Exception:
            pass

    def summary(self) -> dict:
        """今日统计概览（含平均延迟与错误率）。"""
        data = self._load()
        requests = data["requests"]
        data["avg_latency"] = round(data["latency_sum"] / requests, 2) if requests else 0.0
        data["error_rate"] = round(data["errors"] / requests, 4) if requests else 0.0
        data["total_tokens"] = data["prompt_tokens"] + data["completion_tokens"]
        data["cost"] = round(data["cost"], 4)
        return data
