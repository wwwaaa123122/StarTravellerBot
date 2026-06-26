# -*- coding: utf-8 -*-
"""签到插件 - 适配 QQ 开放平台"""

import json
import os
import random
from datetime import datetime, date

TRIGGHT_KEYWORD = "签到"
HELP_MESSAGE = "签到 -> 签到获取积分和好感度"

# 数据文件路径
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "check_in", "users")
os.makedirs(DATA_DIR, exist_ok=True)

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
    defaults = {"points": 0, "affection": 0, "last_checkin": None, "streak": 0}
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 用默认值补全旧数据中缺失的字段
        for k, v in defaults.items():
            data.setdefault(k, v)
        return data
    return defaults.copy()


def _save_data(user_id: str, data: dict):
    """保存用户签到数据"""
    file_path = os.path.join(DATA_DIR, f"{user_id}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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
    """处理签到命令"""
    user_id = event.user_id
    today = date.today().isoformat()
    
    # 加载用户数据
    data = _load_data(user_id)
    
    # 检查是否已签到
    if data["last_checkin"] == today:
        affection_level = _get_affection_level(data["affection"])
        affection_bar = _get_affection_bar(data["affection"])
        
        msg = f"""## 你今天已经签到过了~

- **当前积分**: {data['points']}
- **好感度**: {data['affection']} ({affection_level})
- **进度**: {affection_bar}"""
        await actions.send(content=msg)
        return True
    
    # 计算连续签到
    if data["last_checkin"]:
        last_date = datetime.strptime(data["last_checkin"], "%Y-%m-%d").date()
        if (date.today() - last_date).days == 1:
            data["streak"] += 1
        else:
            data["streak"] = 1
    else:
        data["streak"] = 1
    
    # 计算积分
    base_points = random.randint(10, 30)
    streak_bonus = min(data["streak"] * 2, 50)  # 连续签到奖励，最多50
    total_points = base_points + streak_bonus
    
    # 计算好感度
    base_affection = random.randint(1, 5)
    streak_affection = min(data["streak"], 10)  # 连续签到好感度奖励，最多10
    total_affection = base_affection + streak_affection
    
    # 随机事件
    random_event = random.random()
    event_msg = ""
    
    if random_event < 0.1:  # 10% 概率触发特殊事件
        event_type = random.choice(["lucky", "unlucky"])
        if event_type == "lucky":
            bonus = random.randint(20, 50)
            total_points += bonus
            total_affection += 5
            event_msg = f"\n✨ 今日运势极佳！额外获得 {bonus} 积分和 5 好感度！"
        else:
            penalty = random.randint(5, 15)
            total_points = max(1, total_points - penalty)
            total_affection = max(0, total_affection - 2)
            event_msg = f"\n😅 今日运势不佳...失去 {penalty} 积分和 2 好感度..."
    
    # 更新数据
    data["points"] += total_points
    data["affection"] += total_affection
    data["last_checkin"] = today
    _save_data(user_id, data)
    
    # 获取好感度等级和进度条
    affection_level = _get_affection_level(data["affection"])
    affection_bar = _get_affection_bar(data["affection"])
    
    # 发送签到结果
    msg = f"""## 签到成功！

- **获得积分**: +{total_points}
- **获得好感度**: +{total_affection}
- **连续签到**: {data['streak']} 天
{event_msg}

- **当前积分**: {data['points']}
- **好感度**: {data['affection']} ({affection_level})
- **进度**: {affection_bar}"""
    
    await actions.send(content=msg)
    return True
