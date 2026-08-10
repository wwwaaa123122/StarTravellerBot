# AGENTS.md

## 概述

QQ 开放平台机器人（星辰旅人），基于本项目内 pip 包 `qqbot-openapi`（轻量 SDK，替代旧版 `qq-botpy`）。这是 `XCLR_QQ_bot` 的独立子模块，处理 QQ 频道/群聊/单聊消息，支持插件系统和多模型 AI 对话。

## 运行

```bash
python main.py
```

依赖：本地包 `qqbot-openapi` 及其核心依赖（`httpx`/`aiohttp`）由 `pyproject.toml` 声明，`pip install -e .` 安装；系统状态读取使用内置 `qqbot_openapi.psutil_compat`（纯 Python 实现的 psutil 兼容库，Termux/Android 可用、无需编译，非 Linux 平台可选装 psutil 获得完整能力）；`requirements.txt` 仅含插件额外依赖（如 `python-whois`）。

## 项目结构

```
StarTravellerBot/
├── main.py          # 入口，加载 .env，创建 XCLRClient
├── client.py        # XCLRClient：事件入口 + AI 调度（<300 行）
├── config/          # 配置系统：loader（环境变量 > .env > 默认值）+ schema（类型化访问）
├── core/            # 核心模块：dispatcher（场景路由）/ plugin_manager / messenger / stats / http
├── ai/              # AI 模块（chat / role_manager / roleplay / function_calling）
├── plugins/         # 插件目录，动态加载（TRIGGER_KEYWORD 触发）
├── webadmin/        # Web 管理后台（独立 Flask 服务）
├── data/            # 持久化数据（签到、角色、RAG、统计）
└── .env             # 全部配置（AppID + AppSecret 必填，模板见 .env.example）
```

## 关键依赖关系

`client.py` 从仓库内部模块导入（无父项目依赖）：
- `Tools/core.py` - `BotContext`（运行上下文）+ `VERSION_NAME`（版本常量）
- `Tools/scheduler.py` - APScheduler 调度器（`set_client`/`get_client` 解耦注入）
- `Tools/rag_memory.py` - `RAGMemory`（TF-IDF 对话记忆）
- `ai/` - `AIChat` / `RoleManager` / `roleplay` / `function_calling`
- `core/` - `Dispatcher`（场景路由）/ `PluginManager` / `Messenger` / `StatsTracker` / 共享 HTTP 客户端
- `config/` - 配置加载（环境变量 > .env > 默认值）

## 插件系统

插件放在 `plugins/`，自动加载（排除 `__` 和 `d_` 前缀文件）。

每个插件必须导出：
- `TRIGGER_KEYWORD: str` - 触发关键字（如 `"签到"`, `"ping "`, `"Any"`；旧拼写 `TRIGGHT_*` 仍兼容）
- `HELP_MESSAGE: str` - 帮助描述
- `async def on_message(event, actions, **kwargs)` - 处理函数

`TRIGGER_KEYWORD = "Any"` 的插件匹配所有消息，在具体关键字插件之后执行。

`on_message` 接收的 kwargs 包括：`reminder`, `bot_name`, `ROOT_User`, `config`, `order`, `client` 等（见 `core/plugin_manager.py` 的 `build_kwargs`）。

## AI 对话流程

单聊/频道私信支持 AI 对话，群聊仅支持插件命令。

AI 调用链：`AIChat.run_with_tools`（OpenAI 兼容接口，默认 DeepSeek）或 Gemini。对话历史存在 `BotContext.user_lists`，每用户最多 20 条。

角色系统（`ai/roleplay.py`）优先于默认预设生成系统提示。用户默认角色是 `"tsundere"`（傲娇），不是 `"default"`。

## 配置

全部配置通过 `.env` 文件（或环境变量）提供，模板见 `.env.example`：
- 必填：`STAR_QO_APPID`, `STAR_QO_SECRET`
- AI 密钥、机器人名称/ROOT_User、webadmin、定时群发等均以 `STAR_*` 环境变量配置
- 优先级：环境变量 > `.env` > 默认值（`config/loader.py`）

## 注意事项

- `main.py` 会 `os.chdir(PROJECT_ROOT)` 改变工作目录到仓库根目录
- `main.py` 启动时会临时抑制 stdout（导入时的副作用输出）
- 消息去重使用 `_msg_seq_cache`（基于时间戳的 msg_seq）
- 群聊消息会自动移除 `<@!{robot.id}>` 前缀
- Termux 缺 `tzdata` 时 APScheduler 的 `get_localzone`/`IntervalTrigger` 会抛 `ZoneInfoNotFoundError`：调度器默认回退 UTC，kick 插件显式传 BJT
- 文件编码统一使用 `utf-8`
- 对话语言保持简体中文
- 命名规范：小驼峰（函数/变量）、大驼峰（类）
