import asyncio
import json
import traceback

from Tools.core import BotContext
from Tools.rag_memory import RAGMemory
from ai.role_manager import RoleManager

CONTACT_URL = "https://xc-lr.cn/about"


class AIChat:
    """AI 对话管理器：整合角色系统、RAG 记忆、多模型 API 调用"""

    def __init__(self, config: dict, context: BotContext, rag: RAGMemory,
                 http_client, logger, bot_name: str,
                 role_manager: RoleManager = None,
                 bot_username: str = ""):
        self.config = config
        self.context = context
        self.rag = rag
        self.http_client = http_client
        self.logger = logger
        self.bot_name = bot_name
        self.bot_username = bot_username
        self.role_manager = role_manager or RoleManager()
        self._last_usage = None

    def build_system_prompt(self, user_id: str, user_name: str, query: str) -> str:
        sys_prompt = self.role_manager.get_system_prompt(
            user_id, self.bot_name, user_name, self.bot_username
        )
        rag_context = self.rag.get_relevant_context(user_id, query)
        if rag_context:
            sys_prompt = f"{sys_prompt}\n\n{rag_context}"
        return sys_prompt

    async def run(self, user_id: str, user_name: str, query: str) -> str:
        sys_prompt = self.build_system_prompt(user_id, user_name, query)
        result = await self._api_call(query, sys_prompt, user_id)
        if result:
            asyncio.create_task(self._store_exchange(user_id, query, result))
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

    async def _api_call(self, question: str, sys_prompt: str, user_id: str) -> str:
        mode = self.context.EnableNetwork
        others = self.config.get("Others", {})

        if mode == "GoogleGemini":
            return await self._gemini_call(question, sys_prompt, user_id)

        api_key = others.get("deepseek_key")
        base_url = others.get("ai_base_url", "https://api.deepseek.com")
        model = others.get("ai_model", "deepseek-v4-flash")
        max_tokens = others.get("ai_max_tokens", 2000)
        temperature = others.get("ai_temperature", 0.7)

        if not api_key:
            return "AI 未配置 API Key"

        messages = [{"role": "system", "content": sys_prompt}]
        if user_id in self.context.user_lists:
            for hist in self.context.user_lists[user_id][-5:]:
                messages.append(hist)
        messages.append({"role": "user", "content": question})

        try:
            response = await self.http_client.post(
                f"{base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": False,
                }
            )

            if response.status_code == 200:
                data = response.json()
                self._last_usage = data.get("usage", {})
                result = data["choices"][0]["message"]["content"]

                if user_id not in self.context.user_lists:
                    self.context.user_lists[user_id] = []
                self.context.user_lists[user_id].append({"role": "user", "content": question})
                self.context.user_lists[user_id].append({"role": "assistant", "content": result})
                if len(self.context.user_lists[user_id]) > 20:
                    self.context.user_lists[user_id] = self.context.user_lists[user_id][-20:]

                return result
            else:
                self.logger.error(f"AI API 错误: {response.status_code} {response.text}")
                return f"AI 服务暂时不可用 ({response.status_code})"

        except Exception as e:
            self.logger.error(f"AI 调用错误: {e}")
            return "AI 服务暂时异常，请稍后再试"

    async def run_with_tools(self, user_id: str, user_name: str, query: str,
                             execute_tool_callback, root_users: set) -> str:
        """带 Function Calling 的 AI 对话，支持多轮工具调用"""
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
        if user_id in self.context.user_lists:
            for hist in self.context.user_lists[user_id][-5:]:
                messages.append(hist)
        messages.append({"role": "user", "content": query})

        accumulated_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        for iteration in range(MAX_TOOL_ITERATIONS):
            self._last_usage = None
            response = await self._api_call_with_tools(messages, available_tools)
            if response is None:
                return "AI 服务暂时不可用"

            if self._last_usage:
                for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                    accumulated_usage[key] += self._last_usage.get(key, 0)

            message = response.get("message", {})
            tool_calls = message.get("tool_calls")

            if not tool_calls:
                content = message.get("content", "")
                self._last_usage = accumulated_usage
                if content:
                    if user_id not in self.context.user_lists:
                        self.context.user_lists[user_id] = []
                    self.context.user_lists[user_id].append({"role": "user", "content": query})
                    self.context.user_lists[user_id].append({"role": "assistant", "content": content})
                    if len(self.context.user_lists[user_id]) > 20:
                        self.context.user_lists[user_id] = self.context.user_lists[user_id][-20:]
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
        return "处理超时，请重新提问"

    async def _api_call_with_tools(self, messages: list, tools: list) -> dict | None:
        """带工具定义的 API 调用，返回完整 response choice"""
        mode = self.context.EnableNetwork
        if mode == "GoogleGemini":
            return None

        others = self.config.get("Others", {})
        api_key = others.get("deepseek_key")
        base_url = others.get("ai_base_url", "https://api.deepseek.com")
        model = others.get("ai_model", "deepseek-v4-flash")
        max_tokens = others.get("ai_max_tokens", 2000)
        temperature = others.get("ai_temperature", 0.7)

        if not api_key:
            return None

        try:
            response = await self.http_client.post(
                f"{base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": False,
                    "tools": tools,
                },
            )

            if response.status_code == 200:
                data = response.json()
                self._last_usage = data.get("usage", {})
                return data["choices"][0]
            else:
                self.logger.error(f"AI API 错误: {response.status_code} {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"AI 调用错误: {e}")
            return None

    async def _gemini_call(self, question: str, sys_prompt: str, user_id: str) -> str:
        try:
            import google.generativeai as genai
            api_key = self.config.get("Others", {}).get("gemini_key")
            if not api_key:
                return "Gemini 未配置 API Key"
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            chat = model.start_chat(history=[])
            response = chat.send_message(f"{sys_prompt}\n\n用户问: {question}")
            return response.text
        except Exception as e:
            self.logger.error(f"Gemini 调用错误: {e}")
            return "AI 服务暂时异常，请稍后再试"

    async def _store_exchange(self, user_id: str, question: str, answer: str):
        try:
            self.rag.add_exchange(user_id, question, answer)
        except Exception as e:
            self.logger.error(f"[RAG] 存储对话失败 {user_id}: {e}")
