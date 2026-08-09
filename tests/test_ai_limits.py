# -*- coding: utf-8 -*-
"""AI RateLimiter / CostTracker 测试。"""

import json

from ai.rate_limiter import RateLimiter
from ai.cost_tracker import CostTracker


def test_user_rate_limit():
    limiter = RateLimiter(user_rpm=2, global_rpm=100)
    assert limiter.check("u1") == (True, 0)
    limiter.record("u1")
    assert limiter.check("u1") == (True, 0)
    limiter.record("u1")
    allowed, remaining = limiter.check("u1")
    assert allowed is False
    assert remaining == 0
    # 其他用户不受影响
    assert limiter.check("u2")[0] is True


def test_global_rate_limit():
    limiter = RateLimiter(user_rpm=100, global_rpm=2)
    for i in range(2):
        limiter.record(f"u{i}")
    assert limiter.check("new_user")[0] is False


def test_cost_tracker_record_and_summary(tmp_path):
    tracker = CostTracker(data_dir=str(tmp_path), price_input=1.0, price_output=2.0)
    tracker.record(prompt_tokens=100, completion_tokens=50, latency=0.8)
    tracker.record(prompt_tokens=100, completion_tokens=50, latency=1.2, error=True)
    summary = tracker.summary()
    assert summary["requests"] == 2
    assert summary["total_tokens"] == 300
    assert summary["errors"] == 1
    assert summary["error_rate"] == 0.5
    assert summary["avg_latency"] == 1.0
    # 费用 = 200/1M*1 + 100/1M*2
    assert summary["cost"] == 0.0004


def test_cost_tracker_persists(tmp_path):
    tracker = CostTracker(data_dir=str(tmp_path))
    tracker.record(prompt_tokens=1000, completion_tokens=0)
    data = json.loads((tmp_path / "ai_stats.json").read_text(encoding="utf-8"))
    assert data["requests"] == 1
    assert data["prompt_tokens"] == 1000
    # 新实例读取同一文件
    tracker2 = CostTracker(data_dir=str(tmp_path))
    assert tracker2.summary()["requests"] == 1
