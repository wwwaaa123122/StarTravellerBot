---
prev:
  text: '角色系统'
  link: '/ai/roleplay'
next:
  text: 'API 参考'
  link: '/api/reference'
---

# 工具模块

## Tools.core

`Tools/core.py` 提供最基础的运行上下文和版本信息。

```python
VERSION_NAME = "3.1 - Next Release"


class BotContext:
    """Bot 运行上下文"""

    def __init__(self):
        self.EnableNetwork = "Ds"      # AI 模型模式 ("Ds" / "GoogleGemini")
        self.user_lists = {}           # 对话历史 {user_id: [messages]}
        self.stop_working = False      # 停止工作标志
```

`user_lists` 存储结构：

```python
{
    "user_openid_1": [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好呀~"},
        # ...最多 20 条
    ],
    "user_openid_2": [...]
}
```

## Tools.rag_memory

`Tools/rag_memory.py` 提供基于检索增强生成(RAG)的对话记忆系统。

### 核心原理

使用 **bigram TF-IDF** 进行中文语义检索：

1. 将文本拆分为双字片段（bigram）：`"你好世界" → ["你好", "好世", "世界"]`
2. 计算 TF-IDF 权重，IDF = `ln(N / (1 + df))`
3. 余弦相似度计算相关性
4. 引入**新鲜度权重**：越新的对话权重越高

### API

```python
class RAGMemory:
    def __init__(self, data_dir: str):
        """初始化 RAG 记忆系统"""

    def add_exchange(self, user_id: str, question: str, answer: str):
        """存储一次对话交换"""

    def get_relevant_context(self, user_id: str, query: str) -> str:
        """检索与 query 最相关的历史对话，拼接为上下文文本"""

    def clear_user_history(self, user_id: str):
        """清除用户的所有 RAG 记忆"""
```

### 参数

| 参数 | 默认值 | 说明 |
| :--- | :---: | :--- |
| `top_k` | 3 | 返回最相关的历史条数 |
| `min_relevance` | 0.05 | 最小相关度阈值 |
| `max_tokens` | 800 | 拼接上下文的最大字符数 |

### 存储格式

`data/rag/{user_openid}.json`：

```json
{
  "user_id": "xxx",
  "exchanges": [
    {"q": "你好", "a": "你好呀~", "ts": 1700000000.0},
    {"q": "今天天气", "a": "今天天气不错", "ts": 1700000100.0}
  ]
}
```

最多保留 200 条最近的对话记录。
