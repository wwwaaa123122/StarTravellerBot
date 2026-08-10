# -*- coding: utf-8 -*-

import os
import logging

import aiosqlite

_logger = logging.getLogger("affection")

TRIGGER_KEYWORD = "好感度"
HELP_MESSAGE = "好感度 -> 查询好感度信息"

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "checkin.db")

AFFECTION_LEVELS = [
    (0, "冷漠"),
    (10, "陌生"),
    (30, "熟悉"),
    (50, "友好"),
    (80, "亲密"),
    (120, "信赖"),
    (180, "挚友"),
    (250, "灵魂伴侣"),
]


async def _load_data(user_id: str) -> dict:
    if not os.path.exists(DB_PATH):
        return {"points": 0, "affection": 0, "last_checkin": None, "streak": 0}
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM checkin WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row:
            return {
                "points": row["points"],
                "affection": row["affection"],
                "last_checkin": row["last_checkin"],
                "streak": row["streak"],
            }
    return {"points": 0, "affection": 0, "last_checkin": None, "streak": 0}


def _get_affection_level(affection: int) -> str:
    level = "冷漠"
    for threshold, name in AFFECTION_LEVELS:
        if affection >= threshold:
            level = name
    return level


def _get_affection_bar(affection: int) -> str:
    current_level = AFFECTION_LEVELS[0]
    next_level = AFFECTION_LEVELS[1]
    
    for i, (threshold, name) in enumerate(AFFECTION_LEVELS):
        if affection >= threshold:
            current_level = (threshold, name)
            if i + 1 < len(AFFECTION_LEVELS):
                next_level = AFFECTION_LEVELS[i + 1]
            else:
                next_level = (threshold + 100, "MAX")
    
    current_threshold = current_level[0]
    next_threshold = next_level[0]
    progress = (affection - current_threshold) / (next_threshold - current_threshold) if next_threshold > current_threshold else 1
    progress = min(progress, 1.0)
    
    bar_length = 10
    filled = int(progress * bar_length)
    bar = "█" * filled + "░" * (bar_length - filled)
    
    return f"{bar} {int(progress * 100)}%"


async def on_message(ctx):
    event = ctx.event
    actions = ctx.actions
    kwargs = ctx.kwargs
    user_id = event.user_id
    
    data = await _load_data(user_id)
    
    affection_level = _get_affection_level(data["affection"])
    affection_bar = _get_affection_bar(data["affection"])
    
    next_threshold = None
    for threshold, name in AFFECTION_LEVELS:
        if data["affection"] < threshold:
            next_threshold = threshold
            break
    
    if next_threshold:
        remaining = next_threshold - data["affection"]
        next_level_info = f"距离下一等级还需: {remaining} 好感度"
    else:
        next_level_info = "已达最高等级！"
    
    msg = f"""## 好感度信息

- **好感度**: {data['affection']} ({affection_level})
- **进度**: {affection_bar}
- **当前积分**: {data['points']}
- **连续签到**: {data.get('streak', 0)} 天

{next_level_info}"""
    
    await actions.send(content=msg)
    return True
