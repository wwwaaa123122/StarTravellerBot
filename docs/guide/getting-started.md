---
next:
  text: '消息场景'
  link: '/guide/scenarios'
---

# 快速开始

## 环境要求

- Python 3.10+
- QQ 开放平台机器人账号 ([注册](https://q.qq.com/))
- API Key（DeepSeek / Gemini，用于 AI 对话功能）

## 安装

### 1. 克隆项目

```bash
git clone https://github.com/wwwaaa123122/StarTravellerBot.git
cd StarTravellerBot
```

### 2. 安装依赖

```bash
# 安装本地包 qqbot-openapi 及其核心依赖（httpx/aiohttp；系统状态为内置纯 Python 库，无需 psutil）
pip install -e .
# 安装插件额外依赖（如 python-whois）
pip install -r requirements.txt
```

核心依赖：
- `qqbot-openapi` — QQ 开放平台 SDK（本仓库源码，`pip install -e .` 安装）
- `httpx` — HTTP 客户端
- `psutil_compat` — 系统状态监控（内置纯 Python 实现，Termux/Android 可用，无需编译）

### 3. 配置

复制 `.env.example` 为 `.env` 并填入真实值：

```bash
cp .env.example .env
```

```env
# QQ 开放平台凭证（必填）
STAR_QO_APPID=你的AppID
STAR_QO_SECRET=你的AppSecret
# STAR_QO_SANDBOX=true

# AI API 密钥（至少配置一个）
STAR_DEEPSEEK_KEY=你的DeepSeek密钥
# STAR_GEMINI_KEY=你的Gemini密钥

# 机器人基础信息
# STAR_BOT_NAME=星辰旅人
# STAR_BOT_REMINDER=#
# STAR_BOT_ROOT_USER=你的QQ管理员OpenID
# STAR_BOT_DEFAULT_MODE=Ds
# STAR_BOT_ALLOW_AI=true

# AI 可选配置
# STAR_AI_BASE_URL=https://api.deepseek.com
# STAR_AI_MODEL=deepseek-v4-flash
# STAR_AI_MAX_TOKENS=2000
# STAR_AI_TEMPERATURE=0.7

# Web 管理后台（密码必填）
STAR_TRAVELLER_ADMIN_PASSWORD=你的强密码

# 定时群发
# STAR_SCHEDULED_SEND_TIME=06:00
# STAR_SCHEDULED_SEND_CONTENT=早生蚝
# STAR_SCHEDULED_SEND_GROUPS=群OpenID1
# STAR_SCHEDULED_SEND_ADMIN=管理员OpenID
```

| 配置项 | 说明 | 默认值 |
| :--- | :--- | :---: |
| `STAR_QO_APPID` | QQ 开放平台 AppID | — |
| `STAR_QO_SECRET` | QQ 开放平台 AppSecret | — |
| `STAR_QO_SANDBOX` | 是否沙箱环境 | `true` |
| `STAR_BOT_NAME` | 机器人名称 | `星辰旅人` |
| `STAR_BOT_REMINDER` | AI 对话触发前缀 | `#` |
| `STAR_BOT_ROOT_USER` | 管理员 OpenID 列表（逗号分隔） | 空 |
| `STAR_BOT_DEFAULT_MODE` | AI 模型模式 (`Ds` / `GoogleGemini`) | `Ds` |
| `STAR_BOT_ALLOW_AI` | 是否开启 AI 对话 | `true` |
| `STAR_DEEPSEEK_KEY` | DeepSeek API Key | — |
| `STAR_GEMINI_KEY` | Google Gemini API Key | — |
| `STAR_AI_BASE_URL` | 兼容 OpenAI 格式的 API 地址 | `https://api.deepseek.com` |
| `STAR_AI_MODEL` | 模型名称 | `deepseek-v4-flash` |
| `STAR_SCHEDULED_SEND_*` | 定时群发（时间/内容/群/管理员/开关） | 见 `.env.example` |

::: tip
`STAR_DEEPSEEK_KEY` 和 `STAR_GEMINI_KEY` 二选一即可，通过 `STAR_BOT_DEFAULT_MODE` 切换。
`STAR_AI_BASE_URL` 和 `STAR_AI_MODEL` 仅在使用 DeepSeek 模式时生效。
:::

## 启动

```bash
python main.py
```

启动成功后输出：

```
╔══════════════════════════════════════════════════════════════════╗
║                    星辰旅人 - QQ 开放平台机器人                  ║
║                         Version: 3.1 - Next Release             ║
╚══════════════════════════════════════════════════════════════════╝
```

## 验证运行

在 QQ 上私聊机器人发送 `ping`，应返回 `Ciallo∼(∠・ω[ )⌒☆`

发送 `帮助` 查看所有可用命令。
