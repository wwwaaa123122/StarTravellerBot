# 星辰旅人 - QQ 开放平台机器人

基于 [qq-botpy](https://github.com/tencent-connect/botpy) SDK 的 QQ 开放平台机器人，支持多场景消息分发、插件系统、AI 对话和角色扮演。

## 功能特性

- **多场景支持**: QQ 单聊、群聊@、频道私信、频道@
- **插件系统**: 动态加载插件，支持关键字触发和全局匹配
- **AI 对话**: 集成 DeepSeek / Gemini API，支持角色扮演
- **内置插件**: 签到、天气、Ping、一言、随机图、MC 状态、域名查询、QR 码生成、踢人、定时发送等

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

编辑 `open-qq/.env`（如本项目为独立仓库，则编辑 `.env`）：

```env
AppID=你的AppID
AppSecret=你的AppSecret
```

AI API 密钥等配置在父项目 `XCLR_QQ_bot/config.json` 中。

### 3. 运行

```bash
python open-qq/main.py
```

## 项目结构

```
open-qq/
├── main.py          # 入口，加载配置并创建客户端
├── client.py        # 核心客户端，消息分发 + AI 调用
├── adapters.py      # botpy API 适配器
├── ai/              # AI 模块
│   ├── chat.py         # 对话处理
│   ├── role_manager.py # 角色管理
│   └── roleplay.py     # 角色扮演
├── plugins/         # 插件目录（动态加载）
│   ├── checkin.py      # 签到
│   ├── weather.py      # 天气查询
│   ├── ping.py         # Ping 测试
│   ├── help.py         # 帮助
│   ├── hitokoto.py     # 一言
│   ├── acg_picture.py  # ACG 图片
│   ├── mc_status.py    # Minecraft 状态
│   ├── domain_whois.py # 域名 Whois
│   ├── qr_code.py      # 二维码生成
│   ├── tts.py          # 语音合成
│   ├── kick.py         # 踢人
│   ├── kick_notify.py  # 踢人通知
│   ├── affection.py    # 好感度
│   ├── roleplay.py     # 角色扮演设置
│   ├── scheduled_send.py # 定时发送
│   └── httptest.py     # HTTP 测试
├── data/            # 持久化数据
│   ├── checkin/        # 签到数据
│   ├── rag/            # RAG 记忆
│   ├── roles/          # 角色数据
│   └── scheduled_sent.json
└── Tools/           # 工具模块
    ├── core.py
    └── rag_memory.py   # RAG 记忆
```

## 插件系统

插件放在 `plugins/` 目录，自动加载（排除 `__` 和 `d_` 前缀文件）。

每个插件需导出：

| 导出名 | 类型 | 说明 |
|--------|------|------|
| `TRIGGHT_KEYWORD` | `str` | 触发关键字（如 `"签到"`） |
| `HELP_MESSAGE` | `str` | 帮助描述 |
| `on_message` | `async def` | 消息处理函数 |

`TRIGGHT_KEYWORD = "Any"` 的插件匹配所有消息，在具体关键字插件之后执行。

## 支持的场景

| 场景 | 事件类型 | AI 对话 |
|------|----------|---------|
| QQ 单聊 | `C2C_MESSAGE_CREATE` | ✅ |
| QQ 群聊@机器人 | `GROUP_AT_MESSAGE_CREATE` | ❌（仅插件） |
| 频道私信 | `DIRECT_MESSAGE_CREATE` | ✅ |
| 频道@机器人 | `AT_MESSAGE_CREATE` | ✅ |

## AI 对话

- 默认 AI: DeepSeek API（可切换 Gemini）
- 每用户对话历史上限 20 条
- 默认角色: `tsundere`（傲娇）
- 群聊仅支持插件命令，不支持 AI 对话

## 配置

- `.env`: `AppID`、`AppSecret`（必填）
- `config.json`（父项目）: AI API 密钥、机器人名称、ROOT_User 等
- `is_sandbox=True` 硬编码在 `main.py`

## 注意事项

- 文件编码统一使用 `utf-8`
- 消息去重基于 `msg_seq` 时间戳缓存
- 群聊消息自动移除 `<@!robot_id>` 前缀
- 命名规范：小驼峰（函数/变量）、大驼峰（类）

## 依赖

- `qq-botpy` >= 1.2.0
- `httpx` >= 0.27.0
- `aiohttp` >= 3.9.0
- `psutil` >= 5.9.0

## 文档

- [QQ 开放平台文档](https://bot.q.qq.com/wiki/)
- [botpy SDK 文档](https://bot.q.qq.com/wiki/develop/pythonsdk/)
