# AI 对话

## 概述

AI 对话系统由 `AIChat` 类管理，位于 `ai/chat.py`。支持双模型切换（DeepSeek / Google Gemini），整合角色系统、RAG 记忆和多轮对话上下文。

## 架构

```
用户消息 → AIChat.run()
  ├── RoleManager.get_system_prompt() → 角色 system prompt
  ├── RAGMemory.get_relevant_context() → 相关历史
  ├── 拼接完整 messages
  │   ├── system prompt + RAG 上下文
  │   ├── 最近 5 条对话历史
  │   └── 当前用户消息
  └── API 调用 → 返回回复
```

## 模型配置

### DeepSeek（默认）

```json
{
  "Others": {
    "default_mode": "Ds",
    "deepseek_key": "sk-xxxxxxxxxxxx",
    "ai_base_url": "https://api.deepseek.com",
    "ai_model": "deepseek-v4-flash",
    "ai_max_tokens": 2000,
    "ai_temperature": 0.7
  }
}
```

`ai_base_url` 兼容任何 OpenAI 格式的 API，可替换为其它兼容服务。

### Gemini

```json
{
  "Others": {
    "default_mode": "GoogleGemini",
    "gemini_key": "AIxxxxxxxxxxxx"
  }
}
```

使用 `google.generativeai` SDK，模型为 `gemini-2.0-flash-exp`。

## 上下文管理

对话历史存储在 `BotContext.user_lists` 中，以用户 OpenID 为 key：

- 每次对话自动追加 user 和 assistant 消息
- 最多保留 20 条记录（超限截断）
- 发送 `注销` 命令清除上下文

### RAG 记忆

除了短期对话历史，还有长期 RAG 记忆：

```python
rag.add_exchange(user_id, question, answer)
```

使用 **bigram TF-IDF** 进行中文语义检索，匹配与当前查询最相关的历史对话，拼接进 system prompt。存储路径：`data/rag/{user_id}.json`

## 触发方式

| 场景 | 触发条件 |
| :--- | :--- |
| QQ 单聊 | 直接发送消息（长度>=1）或 `#消息` |
| 频道私信 | 直接发送消息（长度>=2）或 `#消息` |
| 群聊@/频道@ | **不支持** AI 对话 |

## 代码参考

```python
class AIChat:
    def build_system_prompt(self, user_id, user_name, query) -> str:
        """构建 system prompt（角色提示 + RAG 上下文）"""

    async def run(self, user_id, user_name, query) -> str:
        """执行一次 AI 对话，返回回复文本"""

    async def handle_message(self, order, user_id, user_name, send_func) -> bool:
        """带错误处理和用户友好提示的消息处理"""
```
