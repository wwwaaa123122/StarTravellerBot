# -*- coding: utf-8 -*-
"""签到插件 - 适配 QQ 开放平台 (与 [XY]GroupCheckIn 文本模式保持一致)"""

import json
import os
import random
import logging
from datetime import datetime

import aiosqlite
import httpx

_logger = logging.getLogger("checkin")

TRIGGER_KEYWORD = "签到"
HELP_MESSAGE = "签到 -> 签到获取积分和好感度"

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "checkin.db")
# 旧 JSON 数据目录（用于迁移）
JSON_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "checkin")

_db: aiosqlite.Connection | None = None


async def _get_db() -> aiosqlite.Connection:
    """获取数据库连接（懒初始化），启用 WAL 模式提升并发性能。"""
    global _db
    if _db is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _db = await aiosqlite.connect(DB_PATH)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
        await _init_db()
        await _migrate_json()
    return _db


async def _init_db():
    """创建数据表和索引。"""
    await _db.execute(
        """CREATE TABLE IF NOT EXISTS checkin (
            user_id TEXT PRIMARY KEY,
            points INTEGER DEFAULT 0,
            affection INTEGER DEFAULT 0,
            last_checkin TEXT,
            streak INTEGER DEFAULT 0,
            nickname TEXT DEFAULT ''
        )"""
    )
    await _db.execute(
        "CREATE INDEX IF NOT EXISTS idx_checkin_date ON checkin(last_checkin)"
    )
    await _db.commit()


async def _migrate_json():
    """将旧 JSON 文件迁移到 SQLite（仅首次运行）。"""
    if not os.path.isdir(JSON_DIR):
        return

    files = [f for f in os.listdir(JSON_DIR) if f.endswith(".json")]
    if not files:
        return

    # 检查是否已迁移过（表中已有数据则跳过）
    cursor = await _db.execute("SELECT COUNT(*) FROM checkin")
    row = await cursor.fetchone()
    if row and row[0] > 0:
        return

    migrated = 0
    for filename in files:
        filepath = os.path.join(JSON_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        # 兼容旧字段名
        user_id = data.get("user_id") or filename.replace(".json", "")
        if "积分" in data or "好感度" in data or "last_check" in data:
            points = data.get("points", data.get("积分", 0))
            affection = data.get("affection", data.get("好感度", 0))
            last_checkin = data.get("last_checkin", data.get("last_check"))
            streak = data.get("streak", data.get("total_days", 0))
        else:
            points = data.get("points", 0)
            affection = data.get("affection", 0)
            last_checkin = data.get("last_checkin")
            streak = data.get("streak", 0)

        await _db.execute(
            """INSERT OR IGNORE INTO checkin (user_id, points, affection, last_checkin, streak, nickname)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, points, affection, last_checkin, streak, data.get("nickname", "")),
        )
        migrated += 1

    await _db.commit()
    if migrated > 0:
        _logger.info(f"已从 JSON 迁移 {migrated} 条签到数据到 SQLite")


async def _load_data(user_id: str) -> dict:
    """加载用户签到数据"""
    db = await _get_db()
    cursor = await db.execute("SELECT * FROM checkin WHERE user_id = ?", (user_id,))
    row = await cursor.fetchone()
    if row:
        return {
            "user_id": row["user_id"],
            "points": row["points"],
            "affection": row["affection"],
            "last_checkin": row["last_checkin"],
            "streak": row["streak"],
            "nickname": row["nickname"],
        }
    return {"points": 0, "affection": 0, "last_checkin": None, "streak": 0, "nickname": ""}


async def _save_data(user_id: str, data: dict):
    """保存用户签到数据"""
    db = await _get_db()
    await db.execute(
        """INSERT OR REPLACE INTO checkin (user_id, points, affection, last_checkin, streak, nickname)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            data.get("points", 0),
            data.get("affection", 0),
            data.get("last_checkin"),
            data.get("streak", 0),
            data.get("nickname", ""),
        ),
    )
    await db.commit()


async def _get_daily_rank(today: str) -> int:
    """获取今天第几名签到（通过 SQLite COUNT 查询）"""
    db = await _get_db()
    cursor = await db.execute(
        "SELECT COUNT(*) FROM checkin WHERE last_checkin = ?", (today,)
    )
    row = await cursor.fetchone()
    return row[0] + 1


async def _fetch_hitokoto() -> str:
    """获取一言"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://international.v1.hitokoto.cn/", timeout=5.0)
            data = resp.json()
            return f"{data['hitokoto']} —— {data.get('from_who', '未知')}, {data.get('from', '未知')}"
    except Exception:
        return "今日签到，好运连连~"


async def on_message(ctx):
    """处理签到命令"""
    event = ctx.event
    actions = ctx.actions
    kwargs = ctx.kwargs
    user_id = str(event.user_id)
    today = datetime.now().strftime("%Y-%m-%d")

    # 加载用户数据
    data = await _load_data(user_id)

    # 检查是否已签到
    if data["last_checkin"] == today:
        msg = (
            "## 你今天已经签到过了哦~\n"
            "\n"
            f"- 当前好感度：**{data['affection']}**\n"
            f"- 当前积分：**{data['points']}**"
        )
        await actions.send(markdown={"content": msg})
        return True

    # 签到排名
    rank = await _get_daily_rank(today)

    # 计算奖励（与 [XY]GroupCheckIn 文本模式一致）
    favor = random.randint(1, 10)      # 好感度
    points = random.randint(10, 100)   # 积分

    # 更新数据
    nickname = getattr(event, "nickname", "") or ""
    if nickname:
        data["nickname"] = nickname
    data["streak"] = data.get("streak", 0) + 1
    data["affection"] += favor
    data["points"] += points
    data["last_checkin"] = today
    await _save_data(user_id, data)

    # 获取一言
    hitokoto_text = await _fetch_hitokoto()

    # 发送签到结果（Markdown 格式）
    msg = (
        "## 签到成功！\n"
        f"你是第 **{rank}** 名签到的小伙伴\n"
        "\n"
        "| 项目 | 增加值 | 累计 |\n"
        "| :--- | :----: | :--: |\n"
        f"| 好感度 | +{favor} | {data['affection']} |\n"
        f"| 积分 | +{points} | {data['points']} |\n"
        "\n"
        f"> 累计签到 **{data['streak']}** 天\n"
        "---\n"
        f"> {hitokoto_text}"
    )

    await actions.send(markdown={"content": msg})
    return True
