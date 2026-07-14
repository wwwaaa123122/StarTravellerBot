import asyncio
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
