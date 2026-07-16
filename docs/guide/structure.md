# 项目结构

```
StarTravellerBot/
├── main.py                  # 入口：加载配置，创建 XCLRClient
├── client.py                # 核心：XCLRClient(botpy.Client)，消息分发 + AI 调用
├── config.json              # 配置文件（需自行创建）
├── requirements.txt         # Python 依赖
│
├── ai/                      # AI 模块
│   ├── chat.py              # AIChat - 对话管理器（模型调用、上下文管理）
│   ├── role_manager.py      # RoleManager - 角色数据管理
│   └── roleplay.py          # 角色扮演插件（以插件形式集成到主程序）
│
├── plugins/                 # 插件目录
│   ├── ping.py              # Ping 网络检测
│   ├── checkin.py           # 签到系统
│   ├── affection.py         # 好感度查询
│   ├── weather.py           # 天气查询
│   ├── hitokoto.py          # 一言
│   ├── acg_picture.py       # ACG 图片
│   ├── qr_code.py           # 二维码生成
│   ├── domain_whois.py      # 域名 Whois 查询
│   ├── mc_status.py         # Minecraft 服务器状态
│   ├── httptest.py          # HTTP 测试
│   ├── tts.py               # 语音合成
│   ├── scheduled_send.py    # 定时群发（含后台任务）
│   ├── kick.py              # 踢人监控
│   └── kick_notify.py       # 踢人通知
│
├── Tools/                   # 工具模块
│   ├── core.py              # BotContext 运行上下文 + VERSION_NAME
│   └── rag_memory.py        # RAGMemory - 基于 TF-IDF 的对话记忆
│
├── data/                    # 持久化数据
│   ├── checkin/             # 签到数据（按用户 OpenID 存储）
│   ├── roles/               # 角色数据
│   └── rag/                 # RAG 对话历史
│
├── docs/                    # VitePress 文档
│   └── index.md             # 文档首页
│
└── .vitepress/
    └── config.mts           # VitePress 配置
```

## 核心文件说明

| 文件 | 职责 |
| :--- | :--- |
| `main.py` | 入口点，加载 `config.json`，初始化 `XCLRClient`，调用 `client.run()` |
| `client.py` | 继承 `botpy.Client`，处理 6 种消息事件，分发到插件/AI |
| `ai/chat.py` | AI 对话核心，支持 DeepSeek 和 Gemini 双模型 |
| `ai/role_manager.py` | 角色数据的 CRUD，持久化到 JSON |
| `Tools/core.py` | 运行上下文（版本号、AI 模式、对话历史） |

## 数据流程

```
QQ消息 → botpy SDK → XCLRClient.on_*_message_create()
  ├── 内置命令 (ping/帮助/状态/注销)
  ├── 角色命令 (角色 切换/创建/列表...)
  ├── 插件匹配 (按 TRIGGHT_KEYWORD)
  │   ├── 匹配成功 → 插件处理
  │   └── 匹配失败 → AI 对话（仅限单聊/频道私信）
  └── AI 对话
      ├── RoleManager → 生成 system prompt
      ├── RAGMemory → 检索相关历史
      └── API 调用 → 返回回复
```
