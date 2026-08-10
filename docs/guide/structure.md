---
prev:
  text: '消息场景'
  link: '/guide/scenarios'
next:
  text: 'AI 对话'
  link: '/ai/chat'
---

# 项目结构

```
StarTravellerBot/
├── main.py                  # 入口：加载 .env，创建 XCLRClient
├── client.py                # XCLRClient(qqbot_openapi.Client)：事件入口 + AI 调度（<300 行）
├── .env.example             # 配置模板（复制为 .env 并填写）
├── config/                  # 配置系统：defaults + loader（.env/环境变量优先）+ schema（类型化访问）
├── pyproject.toml          # 本地包 qqbot-openapi 元数据 + 核心依赖 + ruff/mypy 配置
├── requirements.txt        # 插件额外依赖（python-whois 等）
│
├── core/                    # 核心模块
│   ├── dispatcher.py        # 消息分发器：按场景配置统一处理 5 种消息来源
│   ├── plugin_manager.py    # 插件扫描/注册/匹配/执行 + 旧版 kwargs 兼容层
│   ├── messenger.py         # 消息发送（文本/Markdown/文件）
│   ├── stats.py             # 消息/AI 统计 + 昵称记录（JSON 原子写入）
│   └── http.py              # 共享 HTTP 客户端（统一超时/连接池/UA）
│
├── ai/                      # AI 模块
│   ├── chat.py              # AIChat - 对话管理器（模型调用、上下文管理、Function Calling）
│   ├── role_manager.py      # RoleManager - 角色数据管理
│   └── roleplay.py          # 角色扮演插件（以插件形式集成到主程序）
│
├── plugins/                 # 插件目录（TRIGGER_KEYWORD 触发，兼容旧拼写 TRIGGHT_*）
│   ├── ping.py              # Ping 网络检测
│   ├── checkin.py           # 签到系统（SQLite）
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
│   ├── bilibili_parse.py    # B站视频解析（封面 + 点赞/投币/收藏数据）
│   └── douyin_parse.py      # 抖音视频解析（封面 + 点赞/评论/转发数据）
│
├── Tools/                   # 工具模块
│   ├── core.py              # BotContext 运行上下文 + VERSION_NAME
│   ├── scheduler.py         # APScheduler 调度器（set_client/get_client 解耦注入）
│   └── rag_memory.py        # RAGMemory - 基于 TF-IDF 的对话记忆
│
├── webadmin/                # Web 管理后台（Flask）
│   ├── server.py            # 管理后台服务（守护线程启动）
│   └── static/              # 前端静态资源（HTML/CSS/JS）
│
├── data/                    # 持久化数据
│   ├── checkin.db           # 签到数据（SQLite）
│   ├── roles/               # 角色数据
│   ├── rag/                 # RAG 对话历史
│   └── webadmin/            # 管理后台数据（密钥、访问统计）
│
├── docs/                    # VitePress 文档
│   ├── index.md             # 文档首页
│   ├── tools/               # 工具模块文档（webadmin 等）
│   └── public/webadmin/     # 管理后台界面截图（webp）
│
└── .vitepress/
    └── config.mts           # VitePress 配置
```

## 核心文件说明

| 文件 | 职责 |
| :--- | :--- |
| `main.py` | 入口点，加载 `.env`，初始化 `XCLRClient`，调用 `client.run()` |
| `client.py` | 继承 `qqbot_openapi.Client`，事件入口，委托给 Dispatcher/PluginManager/AIChat |
| `core/dispatcher.py` | 场景配置驱动的消息分发（单聊/群聊/频道），内置指令 + 插件 + AI 路由 |
| `core/plugin_manager.py` | 插件扫描/注册/匹配/执行，兼容旧版 kwargs 注入 API |
| `core/messenger.py` | 统一消息发送（自动识别群聊/单聊、Markdown 探测） |
| `config/loader.py` | 配置合并：环境变量 > .env > 默认值 |
| `ai/chat.py` | AI 对话核心，OpenAI 兼容接口（DeepSeek/Gemini 双模型） |
| `Tools/scheduler.py` | 全局 APScheduler 单例，`set_client()` 注入客户端引用 |

## 数据流程

```
QQ消息 → qqbot_openapi SDK → XCLRClient.on_*_message_create()
  └── core/dispatcher.py（按场景路由）
      ├── 内置命令 (ping/帮助/状态/注销)
      ├── 角色命令 (角色 切换/创建/列表...)
      ├── 插件匹配 (按 TRIGGER_KEYWORD)
      │   ├── 匹配成功 → 插件处理
      │   └── 匹配失败 → AI 对话（仅限单聊/频道私信）
      └── AI 对话
          ├── RoleManager → 生成 system prompt
          ├── RAGMemory → 检索相关历史
          └── API 调用 → 返回回复
```

