# AGENTS.md

## 概述

QQ 开放平台机器人（星辰旅人），基于 `qq-botpy` SDK。这是 `XCLR_QQ_bot` 的独立子模块，处理 QQ 频道/群聊/单聊消息，支持插件系统和多模型 AI 对话。

## 运行

```bash
# 从父目录运行（不是从 open-qq/ 内部）
python open-qq/main.py

# 或从 open-qq/ 内部
cd open-qq && python main.py
```

依赖用父项目的 `requirements.txt`，核心依赖：`qq-botpy`, `python-dotenv`, `httpx`, `psutil`

## 项目结构

```
open-qq/
├── main.py          # 入口，加载 .env + config.json，创建 XCLRClient
├── client.py        # 核心：XCLRClient(botpy.Client)，消息分发 + AI 调用
├── adapters.py      # botpy API 适配器（频道消息/权限/频道管理）
├── plugins/         # 插件目录，动态加载
├── data/            # 持久化数据（签到、角色）
└── .env             # AppID + AppSecret（必须配置）
```

## 关键依赖关系

`client.py` 从**父项目** `XCLR_QQ_bot/` 导入：
- `core.context.BotContext` - 运行上下文
- `core.constants.VERSION_NAME, PLUGIN_FOLDER, HELP_BG_LOCAL` - 全局常量
- `AI_bot.AIKernal` - AI 内核（延迟加载）
- `AI_bot.ContextManager` - 上下文管理器
- `prerequisites.prerequisite.gen_presets` - 预设生成

父项目的 `config.json` 路径为 `PROJECT_ROOT/config.json`（main.py:52），不是 `open-qq/` 内的。

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

角色系统（`plugins/roleplay.py`）优先于默认预设生成系统提示。用户默认角色是 `"tsundere"`（傲娇），不是 `"default"`。

## 配置

- `open-qq/.env`：`AppID`, `AppSecret`（必填）
- `XCLR_QQ_bot/config.json`：AI API 密钥、机器人名称、ROOT_User 等
- `is_sandbox=True` 硬编码在 main.py:99

## 注意事项

- `main.py` 会 `os.chdir(PROJECT_ROOT)` 改变工作目录到父项目
- `main.py` 启动时会临时抑制 stdout（导入时的副作用输出）
- 消息去重使用 `_msg_seq_cache`（基于时间戳的 msg_seq）
- 群聊消息会自动移除 `<@!{robot.id}>` 前缀
- 文件编码统一使用 `utf-8`
- 对话语言保持简体中文
- 命名规范：小驼峰（函数/变量）、大驼峰（类）
