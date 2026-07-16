# 插件开发

## 插件架构

插件系统采用动态加载架构，运行时自动扫描 `plugins/` 目录加载插件。每个插件是一个独立的 `.py` 文件，通过约定的导出变量和函数与框架交互。

### 插件发现规则

- 文件必须以 `.py` 结尾
- 文件名不能以 `__` 开头（跳过 `__init__.py`、`__pycache__`）
- 文件名不能以 `d_` 开头（用于禁用插件）

### 插件加载流程

```
client.on_ready()
  → _load_plugins()
    → 遍历 plugins/ 目录
    → importlib 动态导入每个模块
    → 检查 TRIGGHT_KEYWORD 和 on_message
    → 注册到 _plugins 列表
    → 检查 background_tasks 函数
    → 排序（"Any" 插件放最后）
    → 创建 asyncio 后台任务
```

## 编写插件

### 最小插件示例

```python
# plugins/hello.py

TRIGGHT_KEYWORD = "你好"
HELP_MESSAGE = "你好 -> 向机器人打招呼"


async def on_message(event, actions, **kwargs):
    """处理消息"""
    await actions.send(content="你好呀！我是机器人~")
    return True
```

### 必需导出

| 导出名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `TRIGGHT_KEYWORD` | `str` | 触发关键字，消息以此开头时触发（`"Any"` 匹配所有） |
| `HELP_MESSAGE` | `str` | 帮助信息，在 `帮助` 命令中展示 |
| `on_message` | `async callable` | 消息处理函数，返回 `True` 表示已处理 |

### on_message 参数

```python
async def on_message(event, actions, **kwargs):
    """
    Args:
        event:     AdaptedEvent，包含 message/user_id/group_id/message_id
        actions:   PluginActions，提供消息发送方法
        **kwargs:  额外参数，见下方说明
    """
```

**event 属性**

| 属性 | 类型 | 说明 |
| :--- | :--- | :--- |
| `message` | `str` | 消息文本内容 |
| `user_id` | `str` | 用户 OpenID |
| `group_id` | `str` | 群 OpenID（群聊时） |
| `message_id` | `str` | 消息 ID |

**actions 方法**

| 方法 | 说明 |
| :--- | :--- |
| `send(content=...)` | 发送文本消息（自动检测 markdown 语法） |
| `send(markdown={...})` | 发送 markdown 消息 |
| `send_file(url, file_type)` | 发送网络文件（1=图片, 2=视频, 3=语音） |
| `send_local_file(path, file_type)` | 发送本地文件（base64 上传） |
| `send_help_image(text)` | 发送帮助文本 |

**kwargs 包含**

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `reminder` | `str` | 提醒前缀（通常为 `#`） |
| `bot_name` | `str` | 机器人名称 |
| `order` | `str` | 原始用户输入 |
| `ROOT_User` | `list` | 管理员 OpenID 列表 |
| `config` | `dict` | 完整配置 |
| `client` | `XCLRClient` | 机器人客户端实例 |
| `plugins` | `list` | 已加载的插件列表 |

### "Any" 关键字插件

将 `TRIGGHT_KEYWORD` 设为 `"Any"` 的插件会匹配所有消息，在所有关键字插件之后执行。适用于：
- 消息日志记录
- 内容过滤
- 兜底回复

```python
TRIGGHT_KEYWORD = "Any"
HELP_MESSAGE = "（通用处理器）"

async def on_message(event, actions, **kwargs):
    # 处理所有未被其他插件匹配的消息
    return True
```

## 后台任务

插件可以导出 `background_tasks` 函数，在机器人就绪后自动启动为 asyncio 后台任务：

```python
async def background_tasks(client):
    """注册为后台任务"""
    while True:
        # 定时执行的操作
        await asyncio.sleep(60)
```

`client` 参数是 `XCLRClient` 实例，可通过 `client.api` 调用 botpy API。

## 调试建议

1. 在插件中使用 `logging.getLogger("your_plugin")` 获取日志器
2. `on_message` 需要返回 `True` 表示已处理消息（阻止其他插件继续匹配）
3. 返回 `False` 或 `None` 表示未处理
4. 插件执行异常不会影响主程序，错误会被日志记录
