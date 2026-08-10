# -*- coding: utf-8 -*-

import json
import os
from typing import List, Optional

_SUMMARY_PROMPT = (
    "你是对话摘要器。把以下对话压缩为 2-4 条要点，"
    "保留用户偏好、事实与约定，用中文，每条一行，不要客套。"
)


class MemoryManager:

    def __init__(self, data_dir: str, provider=None, logger=None):
        self.memories_file = os.path.join(data_dir, "memories.json")
        self.provider = provider
        self.logger = logger

    def _load(self) -> dict:
        try:
            if os.path.exists(self.memories_file):
                with open(self.memories_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            pass
        return {}

    def _save(self, data: dict):
        try:
            os.makedirs(os.path.dirname(self.memories_file), exist_ok=True)
            tmp = self.memories_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.memories_file)
        except OSError:
            pass

    def get_long_term(self, user_id: str) -> str:
        summaries = self._load().get(user_id, [])
        if not summaries:
            return ""
        lines = "\n".join(f"- {s}" for s in summaries[-5:])
        return f"长期记忆（来自过往对话摘要）：\n{lines}"

    async def summarize(self, history: List[dict]) -> Optional[str]:
        if not self.provider or len(history) < 2:
            return None
        transcript = "\n".join(
            f"{m.get('role', '?')}: {str(m.get('content', ''))[:500]}" for m in history
        )
        messages = [
            {"role": "system", "content": _SUMMARY_PROMPT},
            {"role": "user", "content": transcript[:3000]},
        ]
        try:
            choice = await self.provider.chat(messages)
            if not choice:
                return None
            content = choice.get("message", {}).get("content", "") or ""
            return content.strip() or None
        except Exception as e:
            if self.logger:
                self.logger.error(f"[记忆] 摘要生成失败: {e}")
            return None

    async def compact(self, user_id: str, history: List[dict]) -> bool:
        summary = await self.summarize(history)
        if not summary:
            return False
        data = self._load()
        summaries = data.setdefault(user_id, [])
        summaries.append(summary)
        data[user_id] = summaries[-20:]
        self._save(data)
        return True
