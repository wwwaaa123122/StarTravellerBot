# API 参考

## XCLRClient

`client.py` — 继承 `botpy.Client` 的 QQ 开放平台机器人客户端。

### 构造函数

```python
class XCLRClient(botpy.Client):
    def __init__(self, config: Dict[str, Any], **kwargs)
```

**参数**

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `config` | `dict` | 完整配置，从 `config.json` 加载 |

### 属性

| 属性 | 类型 | 说明 |
| :--- | :--- | :--- |
| `config` | `dict` | 完整配置 |
| `bot_name` | `str` | 机器人名称 |
| `bot_name_en` | `str` | 机器人英文名 |
| `reminder` | `str` | AI 触发前缀 |
| `root_users` | `list` | 管理员 OpenID 列表 |
| `context` | `BotContext` | 运行上下文 |
| `allow_ai` | `bool` | AI 对话开关 |
| `rag` | `RAGMemory` | RAG 记忆实例 |
| `role_manager` | `RoleManager` | 角色管理器 |
| `ai_chat` | `AIChat` | AI 对话管理器 |
| `logger` | `botpy.logging.Logger` | 日志器 |

### 事件方法

| 方法 | 触发事件 | 说明 |
| :--- | :--- | :--- |
| `on_ready()` | 机器人就绪 | 加载插件、启动后台任务 |
| `on_c2c_message_create(message)` | QQ 单聊 | 处理 C2C 消息 |
| `on_group_at_message_create(message)` | 群聊@ | 处理群聊@消息 |
| `on_group_message_create(message)` | 群聊全量 | 处理群聊全量消息 |
| `on_direct_message_create(message)` | 频道私信 | 处理频道私信 |
| `on_at_message_create(message)` | 频道@ | 处理频道@消息 |
| `on_group_add_robot(group)` | 机器人入群 | 记录日志 |
| `on_group_del_robot(group)` | 机器人退群 | 记录日志 |
| `on_friend_add(user)` | 好友添加 | 记录日志 |

### 内部方法

| 方法 | 说明 |
| :--- | :--- |
| `_load_plugins()` | 扫描并加载 plugins/ 目录的插件 |
| `_try_plugins(message, order)` | 尝试匹配插件并执行 |
| `_execute_plugin(plugin, message, order)` | 执行单个插件 |
| `_send_message(message, content, ...)` | 发送消息（自动识别群聊/单聊） |
| `_handle_ai_chat(message, order, ...)` | 处理 AI 对话 |
| `_handle_roleplay_command(message, content)` | 处理角色命令 |
| `_get_help_text()` | 生成帮助文本 |
| `_get_status_text()` | 生成状态文本 |
| `_has_markdown_syntax(text)` | 检测文本是否包含 markdown 语法 |

## AIChat

`ai/chat.py` — AI 对话管理器。

```python
class AIChat:
    def __init__(self, config, context, rag, http_client, logger, bot_name, role_manager=None, bot_username="")
```

| 方法 | 说明 |
| :--- | :--- |
| `run(user_id, user_name, query)` | 执行一次 AI 对话 |
| `handle_message(order, user_id, user_name, send_func)` | 带错误处理的消息处理 |
| `build_system_prompt(user_id, user_name, query)` | 构建 system prompt |

## RoleManager

`ai/role_manager.py` — 角色管理。

```python
class RoleManager:
    def __init__(self, data_dir="data/roles")
```

| 方法 | 说明 |
| :--- | :--- |
| `get_system_prompt(user_id, bot_name, user_name, ...)` | 获取用户当前角色的 system prompt |
| `set_user_role(user_id, role_id)` | 设置用户角色 |
| `get_all_roles()` | 获取所有角色 |
| `create_role(name, prompt, creator)` | 创建自定义角色 |
| `delete_role(name_or_id)` | 删除自定义角色 |
| `edit_role(name_or_id, new_prompt)` | 编辑自定义角色提示词 |
| `find_role(name_or_id)` | 查找角色（内置+自定义） |

## BotContext

```python
class BotContext:
    EnableNetwork: str    # AI 模式 "Ds" 或 "GoogleGemini"
    user_lists: dict      # 对话历史缓存
    stop_working: bool    # 停止标志
```

## RAGMemory

```python
class RAGMemory:
    def __init__(self, data_dir)
    def add_exchange(user_id, question, answer)
    def get_relevant_context(user_id, query) -> str
    def clear_user_history(user_id)
```
