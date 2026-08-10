# -*- coding: utf-8 -*-

import json
import os
import sqlite3
import time
from typing import Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class StatsTracker:

    def __init__(self, data_dir: Optional[str] = None, logger=None):
        self.logger = logger
        data_dir = data_dir or os.path.join(PROJECT_ROOT, "data")
        self.stats_file = os.path.join(data_dir, "stats.json")
        self.nickname_file = os.path.join(data_dir, "nickname_map.json")
        self.checkin_db = os.path.join(data_dir, "checkin.db")

    def load_stats(self) -> dict:
        today = time.strftime("%Y-%m-%d")
        default = {
            "total_messages": 0,
            "messages_today": {"date": today, "count": 0},
            "total_ai_calls": 0,
            "ai_calls_today": {"date": today, "count": 0},
            "total_tokens": 0,
            "tokens_today": {"date": today, "count": 0},
        }
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for key in ("messages_today", "ai_calls_today", "tokens_today"):
                    if data.get(key, {}).get("date") != today:
                        data[key] = {"date": today, "count": 0}
                return data
        except (OSError, json.JSONDecodeError):
            pass
        return default

    def save_stats(self, data: dict):
        try:
            os.makedirs(os.path.dirname(self.stats_file), exist_ok=True)
            tmp = self.stats_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.stats_file)
        except OSError:
            pass

    def record_message(self):
        try:
            stats = self.load_stats()
            stats["total_messages"] += 1
            stats["messages_today"]["count"] += 1
            self.save_stats(stats)
        except Exception:
            pass

    def record_ai_call(self, token_count: int = 0):
        try:
            stats = self.load_stats()
            stats["total_ai_calls"] += 1
            stats["ai_calls_today"]["count"] += 1
            if token_count > 0:
                stats["total_tokens"] += token_count
                stats["tokens_today"]["count"] += token_count
            self.save_stats(stats)
        except Exception:
            pass

    def record_nickname(self, user_id: str, nickname: str) -> None:
        if not user_id or not nickname:
            return
        self.save_nickname(user_id, nickname)

        if not os.path.exists(self.checkin_db):
            return
        try:
            conn = sqlite3.connect(self.checkin_db)
            conn.execute(
                "UPDATE checkin SET nickname = ? WHERE user_id = ? AND (nickname IS NULL OR nickname = '')",
                (nickname, user_id),
            )
            conn.commit()
            conn.close()
            if self.logger:
                self.logger.info(f"[昵称] {user_id} -> {nickname}")
        except Exception:
            pass

    def save_nickname(self, user_id: str, nickname: str) -> None:
        if not user_id or not nickname:
            return
        path = self.nickname_file
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {}
            if not isinstance(data, dict):
                data = {}
            if data.get(user_id) == nickname:
                return
            data[user_id] = nickname
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        except (OSError, json.JSONDecodeError):
            pass
