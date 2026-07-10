# -*- coding: utf-8 -*-
"""签到插件 - 适配 QQ 开放平台 (与 [XY]GroupCheckIn 文本模式保持一致)"""

import json
import os
import random
import threading
from datetime import datetime

import httpx

TRIGGHT_KEYWORD = "签到"
HELP_MESSAGE = "签到 -> 签到获取积分和好感度"

# 数据文件路径
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "checkin")
os.makedirs(DATA_DIR, exist_ok=True)

# 每日排名计数器（避免遍历所有文件）
_rank_lock = threading.Lock()
_rank_cache: dict[str, int] = {}
_RANK_CACHE_FILE = os.path.join(DATA_DIR, "_rank_cache.json")


def _load_rank_cache() -> dict[str, int]:
    if os.path.exists(_RANK_CACHE_FILE):
        try:
            with open(_RANK_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_rank_cache(cache: dict):
    with open(_RANK_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)


def _init_rank_cache(today: str):
    """重建当日排名缓存"""
    count = 0
    for filename in os.listdir(DATA_DIR):
        if filename == "_rank_cache.json" or not filename.endswith(".json"):
            continue
        try:
            with open(os.path.join(DATA_DIR, filename), "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("last_checkin") == today:
                    count += 1
        except (json.JSONDecodeError, OSError):
            continue
    _rank_cache[today] = count
    _save_rank_cache(_rank_cache)
    return count


def _load_data(user_id: str) -> dict:
    """加载用户签到数据"""
    file_path = os.path.join(DATA_DIR, f"{user_id}.json")
    defaults = {"points": 0, "affection": 0, "last_checkin": None, "streak": 0}
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "积分" in data or "好感度" in data or "last_check" in data:
            data = {
                "points": data.get("points", data.get("积分", 0)),
                "affection": data.get("affection", data.get("好感度", 0)),
                "last_checkin": data.get("last_checkin", data.get("last_check")),
                "streak": data.get("streak", data.get("total_days", 0)),
            }
        for key, value in defaults.items():
            data.setdefault(key, value)
        return data
    return defaults.copy()


def _save_data(user_id: str, data: dict):
    """保存用户签到数据"""
    file_path = os.path.join(DATA_DIR, f"{user_id}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _get_daily_rank(today: str) -> int:
    """获取今天第几名签到（使用缓存，避免遍历所有文件）"""
    global _rank_cache
    with _rank_lock:
        if today not in _rank_cache:
            _rank_cache = _load_rank_cache()
            if today not in _rank_cache:
                _init_rank_cache(today)
        _rank_cache[today] = _rank_cache.get(today, 0) + 1
        _save_rank_cache(_rank_cache)
    return _rank_cache[today]


async def _fetch_hitokoto() -> str:
    """获取一言"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://international.v1.hitokoto.cn/", timeout=5.0)
            data = resp.json()
            return f"{data['hitokoto']} —— {data.get('from_who', '未知')}, {data.get('from', '未知')}"
    except Exception:
        return "今日签到，好运连连~"


async def on_message(event, actions, **kwargs):
    """处理签到命令"""
    user_id = str(event.user_id)
    today = datetime.now().strftime("%Y-%m-%d")

    # 加载用户数据
    data = _load_data(user_id)

    # 检查是否已签到
    if data["last_checkin"] == today:
        msg = (
            f"## 你今天已经签到过了哦~\n"
            f"\n"
            f"- 当前好感度：**{data['affection']}**\n"
            f"- 当前积分：**{data['points']}**"
        )
        await actions.send(markdown={"content": msg})
        return True

    # 签到排名
    rank = _get_daily_rank(today)

    # 计算奖励（与 [XY]GroupCheckIn 文本模式一致）
    favor = random.randint(1, 10)      # 好感度
    points = random.randint(10, 100)   # 积分

    # 更新数据
    data["streak"] = data.get("streak", 0) + 1
    data["affection"] += favor
    data["points"] += points
    data["last_checkin"] = today
    _save_data(user_id, data)

    # 获取一言
    hitokoto_text = await _fetch_hitokoto()

    # 发送签到结果（Markdown 格式）
    msg = (
        f"## 签到成功！\n"
        f"你是第 **{rank}** 名签到的小伙伴\n"
        f"\n"
        f"| 项目 | 增加值 | 累计 |\n"
        f"| :--- | :----: | :--: |\n"
        f"| 好感度 | +{favor} | {data['affection']} |\n"
        f"| 积分 | +{points} | {data['points']} |\n"
        f"\n"
        f"> 累计签到 **{data['streak']}** 天\n"
        f"---\n"
        f"> {hitokoto_text}"
    )

    await actions.send(markdown={"content": msg})
    return True