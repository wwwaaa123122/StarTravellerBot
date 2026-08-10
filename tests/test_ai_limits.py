# -*- coding: utf-8 -*-

import json

from ai.cost_tracker import CostTracker


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
    assert summary["cost"] == 0.0004


def test_cost_tracker_persists(tmp_path):
    tracker = CostTracker(data_dir=str(tmp_path))
    tracker.record(prompt_tokens=1000, completion_tokens=0)
    data = json.loads((tmp_path / "ai_stats.json").read_text(encoding="utf-8"))
    assert data["requests"] == 1
    assert data["prompt_tokens"] == 1000
    tracker2 = CostTracker(data_dir=str(tmp_path))
    assert tracker2.summary()["requests"] == 1
