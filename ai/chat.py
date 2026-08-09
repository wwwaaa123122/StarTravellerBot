import asyncio
import json
import os
import time
import traceback
from typing import Optional

from Tools.core import BotContext
from Tools.rag_memory import RAGMemory
from ai.role_manager import RoleManager
from ai.providers import create_provider
from ai.rate_limiter import RateLimiter
from ai.cost_tracker import CostTracker

CONTACT_URL = "https://xc-lr.cn/about"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class AIChat:
    """AI 对话管理器：角色系统 + RAG 记忆 + Provider 抽象 + 限流 + 费用统计。"""

    def __init__(self, config: dict, context: BotContext, rag: RAGMemory,
                 http_client, logger, bot_name: str,
                 role_manager: RoleManager = None,
                 bot_username: str = "", cost_tracker: Optional[CostTracker] = None):
        self.config = config
        self.context = context
        self.rag = rag
        self.http_client = http_client
        self.logger = logger
        self.bot_name = bot_name
        self.bot_username = bot_username
        self.role_manager = role_manager or RoleManager()
        self._last_usage = None

        others = config.get("Others", {})
        self.provider = create_provider(self.context.EnableNetwork, config, http_client, logger)
        self.rate_limiter = RateLimiter(
            user_rpm=int(others.get("ai_rate_limit_user", 10)),
            global_rpm=int(others.get("ai_rate_limit_global", 60)),
        )
        self.cost_tracker = cost_tracker or CostTracker(
            os.path.join(PROJECT_ROOT, "data"),
            price_input=float(others.get("ai_price_input", 1.0)),
            price_output=float(others.get("ai_price_output", 2.0)),
            logger=logger,
        )

    def _rate_limit_message(self) -> str:
        return f"请求太频繁了，休息一下再聊吧～（每分钟最多 {self.rate_limiter.user_rpm} 次）"

    def build_system_prompt(self, user_id: str, user_name: str, query: str) -> str:
        sys_prompt = self.role_manager.get_system_prompt(
            user_id, self.bot_name, user_name, self.bot_username
        )
        rag_context = self.rag.get_relevant_context(user_id, query)
        if rag_context:
            sys_prompt = f"{sys_prompt}\n\n{rag_context}"
        return sys_prompt

    def _history_messages(self, user_id: str) -> list:
        if user_id in self.context.user_lists:
            return self.context.user_lists[user_id][-5:]
        return []

    def _append_history(self, user_id: str, question: str, answer: str):
        if user_id not in self.context.user_lists:
            self.context.user_lists[user_id] = []
        self.context.user_lists[user_id].append({"role": "user", "content": question})
        self.context.user_lists[user_id].append({"role": "assistant", "content": answer})
        if len(self.context.user_lists[user_id]) > 20:
            self.context.user_lists[user_id] = self.context.user_lists[user_id][-20:]

    def _track(self, started: float, error: bool = False, usage: Optional[dict] = None):
        usage = usage or {}
        self.cost_tracker.record(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency=time.monotonic() - started,
            error=error,
        )

    async def run(self, user_id: str, user_name: str, query: str) -> Optional[str]:
        allowed, _ = self.rate_limiter.check(user_id)
        if not allowed:
            return self._rate_limit_message()

        sys_prompt = self.build_system_prompt(user_id, user_name, query)
        started = time.monotonic()
        result = await self._api_call(query, sys_prompt, user_id)
        if result:
            self._track(started, usage=self._last_usage)
            self.rate_limiter.record(user_id)
            asyncio.create_task(self._store_exchange(user_id, query, result))
        else:
            self._track(started, error=True)
            self.rate_limiter.record(user_id)
        return result

    async def handle_message(self, order: str, user_id: str, user_name: str,
                             send_func) -> bool:
        try:
            result = await self.run(user_id, user_name, order)
            if result:
                await send_func(result)
                return True
            return False
        except TimeoutError:
            await send_func(f"😅 哎呀，你问的问题太复杂了，**{self.bot_name}** 想不出来了 ┭┮﹏┭┮")
            return False
        except Exception as e:
            self.logger.error(f"AI 对话错误: {traceback.format_exc()}")
            await send_func(f"😵 **{self.bot_name}** 发生错误了，请稍后再试 ε(┬┬﹏┬┬)3\n\n错误信息: {e}\n联系管理员: {CONTACT_URL}")
            return False

    async def _api_call(self, question: str, sys_prompt: str, user_id: str) -> Optional[str]:
        """无工具调用路径；失败返回 None。"""
        messages = [{"role": "system", "content": sys_prompt}]
        messages.extend(self._history_messages(user_id))
        messages.append({"role": "user", "content": question})

        choice = await self.provider.chat(messages)
        if not choice:
            return None
        self._last_usage = self.provider.get_usage()
        result = choice.get("message", {}).get("content", "")
        if not result:
            return None
        self._append_history(user_id, question, result)
        return result

    async def run_with_tools(self, user_id: str, user_name: str, query: str,
                             execute_tool_callback, root_users: set) -> Optional[str]:
        """带 Function Calling 的 AI 对话，支持多轮工具调用。"""
        allowed, _ = self.rate_limiter.check(user_id)
        if not allowed:
            return self._rate_limit_message()

        from ai.function_calling import (
            get_available_tools,
            FUNCTION_CALLING_SYSTEM_PROMPT,
            MAX_TOOL_ITERATIONS,
        )

        available_tools = get_available_tools(user_id, root_users)
        if not available_tools:
            return await self.run(user_id, user_name, query)

        sys_prompt = self.build_system_prompt(user_id, user_name, query)
        sys_prompt = f"{sys_prompt}\n\n{FUNCTION_CALLING_SYSTEM_PROMPT}"

        messages = [{"role": "system", "content": sys_prompt}]
        messages.extend(self._history_messages(user_id))
        messages.append({"role": "user", "content": query})

        started = time.monotonic()
        accumulated_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        for iteration in range(MAX_TOOL_ITERATIONS):
            self._last_usage = None
            response = await self.provider.chat(messages, tools=available_tools)
            if response is None:
                self._track(started, error=True)
                self.rate_limiter.record(user_id)
                return None

            if self.provider.get_usage():
                for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                    accumulated_usage[key] += self.provider.get_usage().get(key, 0)

            message = response.get("message", {})
            tool_calls = message.get("tool_calls")

            if not tool_calls:
                content = message.get("content", "")
                self._last_usage = accumulated_usage
                self._track(started, usage=accumulated_usage)
                self.rate_limiter.record(user_id)
                if content:
                    self._append_history(user_id, query, content)
                    asyncio.create_task(self._store_exchange(user_id, query, content))
                return content

            self.logger.info(f"[Function Calling] 轮次 {iteration + 1}: AI 调用 {len(tool_calls)} 个工具")
            for tc in tool_calls:
                self.logger.info(f"  -> {tc['function']['name']}({tc['function']['arguments']})")

            messages.append({
                "role": "assistant",
                "content": message.get("content"),
                "tool_calls": tool_calls,
            })

            for tool_call in tool_calls:
                func = tool_call["function"]
                tool_name = func["name"]
                try:
                    arguments = json.loads(func["arguments"])
                except json.JSONDecodeError:
                    arguments = {}

                self.logger.info(f"[Function Calling] 执行工具: {tool_name}")
                result = await execute_tool_callback(tool_name, arguments)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": result,
                })
                self.logger.info(f"[Function Calling] 工具结果 ({len(result)} 字符)")

        self._last_usage = accumulated_usage
        self._track(started, usage=accumulated_usage)
        self.rate_limiter.record(user_id)
        return "处理超时，请重新提问"

    async def _store_exchange(self, user_id: str, question: str, answer: str):
        try:
            self.rag.add_exchange(user_id, question, answer)
        except Exception as e:
            self.logger.error(f"[RAG] 存储对话失败 {user_id}: {e}")
