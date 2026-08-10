# -*- coding: utf-8 -*-

import json

from core.stats import StatsTracker


def test_record_message(tmp_path):
    tracker = StatsTracker(data_dir=str(tmp_path))
    tracker.record_message()
    tracker.record_message()
    data = json.loads((tmp_path / "stats.json").read_text(encoding="utf-8"))
    assert data["total_messages"] == 2
    assert data["messages_today"]["count"] == 2


def test_record_ai_call_tokens(tmp_path):
    tracker = StatsTracker(data_dir=str(tmp_path))
    tracker.record_ai_call(123)
    data = json.loads((tmp_path / "stats.json").read_text(encoding="utf-8"))
    assert data["total_ai_calls"] == 1
    assert data["total_tokens"] == 123


def test_nickname_map_roundtrip(tmp_path):
    tracker = StatsTracker(data_dir=str(tmp_path))
    tracker.record_nickname("openid-1", "小明")
    tracker.record_nickname("openid-1", "小明")
    data = json.loads((tmp_path / "nickname_map.json").read_text(encoding="utf-8"))
    assert data == {"openid-1": "小明"}


def test_empty_nickname_ignored(tmp_path):
    tracker = StatsTracker(data_dir=str(tmp_path))
    tracker.record_nickname("", "x")
    tracker.record_nickname("u", "")
    assert not (tmp_path / "nickname_map.json").exists()
