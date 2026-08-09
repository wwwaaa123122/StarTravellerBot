# 星辰旅人 - QQ 开放平台机器人

基于 [qqbot-openapi](https://github.com/wwwaaa123122/StarTravellerBot)（仓库内 pip 包，QQ 开放平台轻量 SDK）的 QQ 开放平台机器人，支持多场景消息分发、插件系统、AI 对话和角色扮演。

## 功能特性

- **多场景支持**: QQ 单聊、群聊@、频道私信、频道@
- **插件系统**: 动态加载插件，支持关键字触发和全局匹配
- **AI 对话**: 集成 DeepSeek / Gemini API，支持角色扮演与 Function Calling
- **内置插件**: 签到、天气、Ping、一言、随机图、MC 状态、域名查询、QR 码生成、踢人、定时发送等
- **Web 管理后台**: 状态监控、插件/角色/AI 配置管理

## 快速开始

### 1. 安装依赖

```bash
# 安装本地包 qqbot-openapi 及其核心依赖（httpx/aiohttp；系统状态为内置纯 Python 库，无需 psutil）
pip install -e .
# 安装插件额外依赖（如 python-whois）
pip install -r requirements.txt
```

### 2. 配置

复制 `.env.example` 为 `.env` 并填入真实值：

```bash
cp .env.example .env
```

```env
STAR_QO_APPID=你的AppID
STAR_QO_SECRET=你的AppSecret
STAR_DEEPSEEK_KEY=你的DeepSeek密钥
STAR_TRAVELLER_ADMIN_PASSWORD=管理后台密码
```

AI 相关配置（模型、base_url、max_tokens 等）在仓库根目录 `config.json` 的 `Others` 段，环境变量优先级更高。

### 3. 运行

```bash
python main.py
```

## 项目结构

```
StarTravellerBot/
├── main.py          # 入口，加载 .env + config.json，创建 XCLRClient
├── config.json      # 机器人配置（AI 密钥、机器人名称、ROOT_User 等）
├── client.py        # 核心客户端，消息分发 + AI 调用
├── core/            # 核心模块
│   ├── plugin_manager.py  # 插件加载/匹配/执行
│   ├── messenger.py       # 消息发送（文本/Markdown/文件）
│   └── stats.py           # 消息/AI 统计与昵称记录
├── qqbot_openapi/   # 轻量 SDK：鉴权/API/网关 + psutil_compat（纯 Python 系统状态库）
├── ai/              # AI 模块
│   ├── chat.py          # 对话处理（Function Calling）
│   ├── role_manager.py  # 角色管理
│   └── roleplay.py      # 角色扮演
├── plugins/         # 插件目录（动态加载）
│   ├── checkin.py      # 签到
│   ├── weather.py      # 天气查询
│   ├── ping.py         # Ping 测试
│   ├── hitokoto.py     # 一言
│   ├── acg_picture.py  # ACG 图片
│   ├── mc_status.py    # Minecraft 状态
│   ├── domain_whois.py # 域名 Whois
│   ├── qr_code.py      # 二维码生成
│   ├── tts.py          # 语音合成
│   ├── kick.py         # 踢人/直播监控
│   ├── affection.py    # 好感度
│   ├── scheduled_send.py # 定时发送
│   └── httptest.py     # HTTP 测试
├── webadmin/        # Web 管理后台（独立 Flask 服务）
├── data/            # 持久化数据
│   ├── checkin.db      # 签到数据（SQLite）
│   ├── rag/            # RAG 记忆
│   ├── roles/          # 角色数据
│   └── stats.json      # 统计
└── Tools/           # 工具模块
    ├── core.py
    ├── scheduler.py    # APScheduler 调度器
    └── rag_memory.py   # RAG 记忆
```

## 插件系统

插件放在 `plugins/` 目录，自动加载（排除 `__` 和 `d_` 前缀文件）。

每个插件需导出：

| 导出名 | 类型 | 说明 |
|--------|------|------|
| `TRIGGER_KEYWORD` | `str` | 触发关键字（如 `"签到"`） |
| `TRIGGER_KEYWORDS` | `list[str]` | 多关键字（可选，优先于 `TRIGGER_KEYWORD`） |
| `HELP_MESSAGE` | `str` | 帮助描述 |
| `on_message` | `async def` | 消息处理函数 |

`TRIGGER_KEYWORD = "Any"` 的插件匹配所有消息，在具体关键字插件之后执行。

> 旧拼写 `TRIGGHT_KEYWORD` / `TRIGGHT_KEYWORDS` 仍被兼容识别，但新插件请使用 `TRIGGER_*`。

## 支持的场景

| 场景 | 事件类型 | AI 对话 |
|------|----------|---------|
| QQ 单聊 | `C2C_MESSAGE_CREATE` | ✅ |
| QQ 群聊@机器人 | `GROUP_AT_MESSAGE_CREATE` | ❌（仅插件） |
| 频道私信 | `DIRECT_MESSAGE_CREATE` | ✅ |
| 频道@机器人 | `AT_MESSAGE_CREATE` | ✅ |

## AI 对话

- 默认 AI: DeepSeek API（OpenAI 兼容接口，可切换 Gemini）
- 每用户对话历史上限 20 条
- 默认角色: `tsundere`（傲娇）
- 群聊仅支持插件命令，不支持 AI 对话

## 配置

配置优先级：环境变量 > `.env` > `config.json` > 内置默认值。

- `.env`: `STAR_QO_APPID`、`STAR_QO_SECRET`（必填）、AI 密钥、管理后台密码
- `config.json`: AI 模型参数、机器人名称、ROOT_User、webadmin 等

## 注意事项

- 文件编码统一使用 `utf-8`
- 消息去重基于 `msg_seq` 时间戳缓存
- 群聊消息自动移除 `<@!robot_id>` 前缀
- 命名规范：小驼峰（函数/变量）、大驼峰（类）

## 依赖

- `qqbot-openapi`（本仓库源码，`pip install -e .` 安装）
- `httpx` >= 0.27.0
- `aiohttp` >= 3.9.0
- `psutil_compat`（内置纯 Python 实现，Termux/Android 可用；非 Linux 平台可自行安装 `psutil`）

## 文档

- [QQ 开放平台文档](https://bot.q.qq.com/wiki/)
