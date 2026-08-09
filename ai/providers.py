# -*- coding: utf-8 -*-
"""AI Provider 抽象：OpenAI 兼容 / Gemini 统一接口。

接入新模型只需实现 AIProvider.chat()，核心不感知具体厂商。
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class AIProvider(ABC):
    """模型调用抽象；last_usage 保存最近一次调用的 token 用量。"""

    name: str = "base"

    def __init__(self, config: dict, http_client, logger):
        self.config = config
        self.http_client = http_client
        self.logger = logger
        self.last_usage: dict = {}

    @abstractmethod
    async def chat(self, messages: List[dict], tools: Optional[List[dict]] = None, **kwargs) -> Optional[Dict[str, Any]]:
        """调用模型，返回 OpenAI 风格 choice（含 message/tool_calls），失败返回 None。"""

    def get_usage(self) -> dict:
        return self.last_usage


class OpenAICompatibleProvider(AIProvider):
    """DeepSeek / OpenAI / SiliconFlow / Moonshot 等所有 OpenAI 兼容接口。"""

    name = "openai-compatible"

    def __init__(self, config: dict, http_client, logger):
        super().__init__(config, http_client, logger)
        others = config.get("Others", {})
        self.api_key = others.get("deepseek_key") or others.get("openai_key")
        self.base_url = others.get("ai_base_url", "https://api.deepseek.com")
        self.model = others.get("ai_model", "deepseek-v4-flash")
        self.max_tokens = others.get("ai_max_tokens", 2000)
        self.temperature = others.get("ai_temperature", 0.7)

    async def chat(self, messages, tools=None, **kwargs) -> Optional[dict]:
        if not self.api_key:
            return None
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
        try:
            response = await self.http_client.post(
                f"{self.base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if response.status_code == 200:
                data = response.json()
                self.last_usage = data.get("usage", {})
                return data["choices"][0]
            self.logger.error(f"AI API 错误: {response.status_code} {response.text}")
            return None
        except Exception as e:
            self.logger.error(f"AI 调用错误: {e}")
            return None


class GeminiProvider(AIProvider):
    """Google Gemini（google.generativeai 官方库）。"""

    name = "gemini"

    async def chat(self, messages, tools=None, **kwargs) -> Optional[dict]:
        try:
            import google.generativeai as genai

            api_key = self.config.get("Others", {}).get("gemini_key")
            if not api_key:
                return None
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            system_prompt = next((m["content"] for m in messages if m.get("role") == "system"), "")
            user_question = messages[-1]["content"] if messages else ""
            response = model.generate_content(f"{system_prompt}\n\n用户问: {user_question}")
            return {"message": {"content": response.text, "tool_calls": None}, "finish_reason": "stop"}
        except Exception as e:
            self.logger.error(f"Gemini 调用错误: {e}")
            return None


def create_provider(mode: str, config: dict, http_client, logger) -> AIProvider:
    """按模式创建 provider；未知模式回退 OpenAI 兼容。"""
    if mode == "GoogleGemini":
        return GeminiProvider(config, http_client, logger)
    return OpenAICompatibleProvider(config, http_client, logger)
