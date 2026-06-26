# AGENTS.md

## 概述

QQ 开放平台机器人（星辰旅人），基于 `qq-botpy` SDK。已完全独立，不依赖父项目 `XCLR_QQ_bot/` 的任何 Python 模块。

## 运行

```bash
cd open-qq && python main.py
```

依赖：`qq-botpy`, `python-dotenv`, `httpx`, `aiohttp`, `psutil`

## 项目结构

```
open-qq/
├── main.py          # 入口，加载 config.json，创建 XCLRClient
├── client.py        # 核心：XCLRClient(botpy.Client)，消息分发 + AI 调用
├── core.py          # BotContext + VERSION_NAME（本地版，无父依赖）
├── rag_memory.py    # RAG 对话记忆（TF-IDF 检索）
├── adapters.py      # botpy API 适配器
├── plugins/         # 插件目录，动态加载
├── data/            # 持久化数据（签到、角色、RAG 记忆）
└── .env             # AppID + AppSecret（可选，优先使用 config.json）
```

## 配置来源

配置优先加载 `open-qq/config.json`（本地），不存在则回退到父目录 `XCLR_QQ_bot/config.json`。

## 插件系统

插件放在 `open-qq/plugins/`，自动加载（排除 `__` 和 `d_` 前缀文件）。

每个插件必须导出：
- `TRIGGHT_KEYWORD: str` - 触发关键字（如 `"签到"`, `"ping "`, `"Any"`）
- `HELP_MESSAGE: str` - 帮助描述
- `async def on_message(event, actions, **kwargs)` - 处理函数

`TRIGGHT_KEYWORD = "Any"` 的插件匹配所有消息，在具体关键字插件之后执行。

`on_message` 接收的 kwargs 包括：`reminder`, `bot_name`, `ROOT_User`, `config`, `order` 等（见 client.py:247-279）。

## AI 对话流程

单聊/频道私信支持 AI 对话，群聊仅支持插件命令。

AI 调用链：`_simple_ai_call` -> DeepSeek API（默认）或 Gemini。对话历史存在 `BotContext.user_lists`，每用户最多 20 条。

RAG 记忆：每轮对话通过 `rag_memory.py` 持久化存储，用户提问时自动检索 top-3 相关历史对话作为上下文。

角色系统（`plugins/roleplay.py`）优先于默认预设生成系统提示。用户默认角色是 `"tsundere"`（傲娇），不是 `"default"`。

## 配置

- `config.json`：包含 OpenQQ.appid/secret、AI API 密钥、机器人名称等
- `.env`：AppID/AppSecret 备用
- `is_sandbox=False` 硬编码在 main.py

## 注意事项

- 消息去重使用 `_msg_seq_cache`（基于时间戳的 msg_seq）
- 群聊消息会自动移除 `<@!{robot.id}>` 前缀
- 文件编码统一使用 `utf-8`
- 对话语言保持简体中文
- 命名规范：小驼峰（函数/变量）、大驼峰（类）
