# -*- coding: utf-8 -*-
"""好感度查询插件 - 适配 QQ 开放平台"""

import json
import os
import logging
_logger = logging.getLogger("affection")
import logging

TRIGGHT_KEYWORD = "好感度"
HELP_MESSAGE = "好感度 -> 查询好感度信息"

# 数据文件路径
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "checkin")

# 好感度等级
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


def _load_data(user_id: str) -> dict:
    """加载用户签到数据"""
    file_path = os.path.join(DATA_DIR, f"{user_id}.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"points": 0, "affection": 0, "last_checkin": None, "streak": 0}


def _get_affection_level(affection: int) -> str:
    """获取好感度等级"""
    level = "冷漠"
    for threshold, name in AFFECTION_LEVELS:
        if affection >= threshold:
            level = name
    return level


def _get_affection_bar(affection: int) -> str:
    """获取好感度进度条"""
    # 找到当前等级和下一等级
    current_level = AFFECTION_LEVELS[0]
    next_level = AFFECTION_LEVELS[1]
    
    for i, (threshold, name) in enumerate(AFFECTION_LEVELS):
        if affection >= threshold:
            current_level = (threshold, name)
            if i + 1 < len(AFFECTION_LEVELS):
                next_level = AFFECTION_LEVELS[i + 1]
            else:
                next_level = (threshold + 100, "MAX")
    
    # 计算进度
    current_threshold = current_level[0]
    next_threshold = next_level[0]
    progress = (affection - current_threshold) / (next_threshold - current_threshold) if next_threshold > current_threshold else 1
    progress = min(progress, 1.0)
    
    # 生成进度条
    bar_length = 10
    filled = int(progress * bar_length)
    bar = "█" * filled + "░" * (bar_length - filled)
    
    return f"{bar} {int(progress * 100)}%"


async def on_message(event, actions, **kwargs):
    """查询好感度"""
    user_id = event.user_id
    
    # 加载用户数据
    data = _load_data(user_id)
    
    # 获取好感度等级和进度条
    affection_level = _get_affection_level(data["affection"])
    affection_bar = _get_affection_bar(data["affection"])
    
    # 计算下一等级所需好感度
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
