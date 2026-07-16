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
pip install -r requirements.txt
```

核心依赖：
- `qq-botpy` — QQ 开放平台 Python SDK
- `httpx` — HTTP 客户端
- `python-dotenv` — 环境变量管理
- `psutil` — 系统状态监控

### 3. 配置

在项目根目录创建 `config.json`：

```json
{
  "OpenQQ": {
    "appid": "你的AppID",
    "secret": "你的AppSecret",
    "sandbox": true
  },
  "Others": {
    "bot_name": "星辰旅人",
    "bot_name_en": "XCLR",
    "reminder": "#",
    "ROOT_User": ["你的QQ管理员OpenID"],
    "default_mode": "Ds",
    "allow_ai": true,
    "deepseek_key": "sk-xxxxxxxxxxxx",
    "gemini_key": "AIxxxxxxxxxxxx",
    "ai_base_url": "https://api.deepseek.com",
    "ai_model": "deepseek-v4-flash",
    "ai_max_tokens": 2000,
    "ai_temperature": 0.7
  },
  "scheduled_send": {
    "admin_user": "管理员OpenID",
    "notify_groups": ["群OpenID1"],
    "send_time": "06:00",
    "default_content": "早生蚝"
  },
  "Log_level": "INFO"
}
```

| 配置项 | 说明 | 默认值 |
| :--- | :--- | :---: |
| `OpenQQ.appid` | QQ 开放平台 AppID | — |
| `OpenQQ.secret` | QQ 开放平台 AppSecret | — |
| `OpenQQ.sandbox` | 是否沙箱环境 | `true` |
| `Others.bot_name` | 机器人名称 | `星辰旅人` |
| `Others.reminder` | AI 对话触发前缀 | `#` |
| `Others.ROOT_User` | 管理员 OpenID 列表 | `[]` |
| `Others.default_mode` | AI 模型模式 (`Ds` / `GoogleGemini`) | `Ds` |
| `Others.allow_ai` | 是否开启 AI 对话 | `true` |
| `Others.deepseek_key` | DeepSeek API Key | — |
| `Others.gemini_key` | Google Gemini API Key | — |
| `Others.ai_base_url` | 兼容 OpenAI 格式的 API 地址 | `https://api.deepseek.com` |
| `Others.ai_model` | 模型名称 | `deepseek-v4-flash` |

::: tip
`deepseek_key` 和 `gemini_key` 二选一即可，通过 `default_mode` 切换。
`ai_base_url` 和 `ai_model` 仅在使用 DeepSeek 模式时生效。
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
