---
prev:
  text: 'Web 管理后台'
  link: '/tools/webadmin'
---

# API 参考

本文档覆盖 `qqbot-openapi` SDK 的全部公开类与函数：调用方法、参数说明、返回值与代码示例。

## 快速开始

```bash
pip install qqbot-openapi
```

最小可用机器人（阻塞运行）：

```python
from qqbot_openapi import Client, Intents

# 订阅事件：频道@、群聊/C2C、频道私信
intents = Intents(
    public_guild_messages=True,
    public_messages=True,
    direct_message=True,
)


class MyBot(Client):
    async def on_ready(self, event):
        print("机器人就绪:", event)

    async def on_c2c_message_create(self, message):
        await message.reply(content="你好！")


client = MyBot(intents=intents)
client.run(appid="你的 AppID", secret="你的 AppSecret")
```

- 消息回复统一使用 `message.reply(...)`，SDK 会自动识别群聊 / C2C / 频道场景。

## Client

`qqbot_openapi.client.Client` — 机器人客户端基类。子类通过定义 `on_xxx` 方法接收网关事件。

### 构造函数

```python
Client(intents=None, log_level=None, **kwargs)
```

| 参数 | 类型 | 说明 |
| :--- | :--- | :--- |
| `intents` | `Intents` | 事件订阅集合，缺省为 `Intents()`（不订阅任何事件） |
| `log_level` | `int` | 设置根日志级别（如 `logging.DEBUG`），可选 |

### 属性

| 属性 | 类型 | 说明 |
| :--- | :--- | :--- |
| `intents` | `Intents` | 事件订阅集合 |
| `api` | `API` | REST API 客户端（`start()` 后可用） |
| `robot` | `Model` | 机器人自身信息（READY 后可用，如 `robot.id`、`robot.username`） |

### 方法

#### run(appid, secret)

```python
def run(self, appid: str, secret: str) -> None
```

阻塞运行入口，与旧版 `botpy` 的 `client.run(appid, secret)` 兼容。内部创建事件循环并持续运行网关，进程退出前不会返回。

**示例**

```python
client = MyBot(intents=intents)
client.run(appid="1234567890", secret="your-app-secret")
```

#### start(appid, secret)

```python
async def start(self, appid: str, secret: str) -> None
```

异步启动：初始化鉴权、REST API 与 WebSocket 网关连接。适合在已有事件循环中使用。

**示例**

```python
import asyncio

async def main():
    client = MyBot(intents=intents)
    await client.start(appid="1234567890", secret="your-app-secret")

asyncio.run(main())
```

#### close()

```python
async def close(self) -> None
```

释放网络资源（token 管理器与 HTTP 会话）。

**示例**

```python
try:
    await client.start(appid, secret)
finally:
    await client.close()
```

### 事件回调

在 `Client` 子类中定义以下异步方法即可接收对应事件。回调参数由 SDK 包装为数据模型，字段即属性（缺失字段返回 `None`）。

| 回调方法 | 触发事件 | 参数模型 | 说明 |
| :--- | :--- | :--- | :--- |
| `on_ready(event)` | `READY` | `Ready` | 网关连接就绪，`session_id`/`shard`/`user` |
| `on_c2c_message_create(message)` | `C2C_MESSAGE_CREATE` | `GroupMessage` | 单聊（C2C）消息 |
| `on_group_at_message_create(message)` | `GROUP_AT_MESSAGE_CREATE` | `GroupMessage` | 群聊 @ 消息 |
| `on_group_message_create(message)` | `GROUP_MESSAGE_CREATE` | `GroupMessage` | 群聊全量消息 |
| `on_direct_message_create(message)` | `DIRECT_MESSAGE_CREATE` | `DirectMessage` | 频道私信 |
| `on_at_message_create(message)` | `AT_MESSAGE_CREATE` | `Message` | 频道 @ 消息 |
| `on_group_add_robot(event)` | `GROUP_ADD_ROBOT` | `Group` | 机器人被拉入群 |
| `on_group_del_robot(event)` | `GROUP_DEL_ROBOT` | `Group` | 机器人被移出群 |
| `on_group_msg_reject(event)` | `GROUP_MSG_REJECT` | `Group` | 群主关闭机器人消息权限 |
| `on_group_msg_receive(event)` | `GROUP_MSG_RECEIVE` | `Group` | 群主重新开启机器人消息权限 |
| `on_c2c_msg_receive(event)` | `C2C_MSG_RECEIVE` | `C2CMsgReceive` | 用户开启机器人单聊主动消息 |
| `on_c2c_msg_reject(event)` | `C2C_MSG_REJECT` | `C2CMsgReject` | 用户关闭机器人单聊主动消息 |
| `on_subscribe_message_status(event)` | `SUBSCRIBE_MESSAGE_STATUS` | `SubscribeMessageStatus` | 用户订阅授权状态变更（模板授权） |
| `on_friend_add(event)` | `FRIEND_ADD` | `FriendUser` | 好友添加 |
| `on_friend_del(event)` | `FRIEND_DEL` | `FriendUser` | 好友删除 |

**示例**

```python
class MyBot(Client):
    async def on_group_at_message_create(self, message):
        # message.author.user_openid 为触发用户；message.group_openid 为群标识
        await message.reply(content=f"收到 @，来自 {message.author.user_openid}")

    async def on_group_add_robot(self, event):
        print(f"进群 {event.group_openid}，操作人 {event.op_member_openid}")

    async def on_at_message_create(self, message):
        # 频道 @ 消息
        await message.reply(markdown=f"**{message.content}**")
```

## Intents

`qqbot_openapi.intents.Intents` — 网关事件订阅集合（Identify 的 intents 字段）。

### 构造函数

```python
Intents(**kwargs)
```

按关键字开关订阅，传入 `True` 启用，`False`/省略不启用。

**示例**

```python
from qqbot_openapi import Intents

intents = Intents(
    guilds=True,               # 频道事件（频道增删、成员变动等）
    guild_members=True,        # 频道成员事件
    public_guild_messages=True,  # 频道 @ 消息（AT_MESSAGE_CREATE）
    public_messages=True,      # 群聊 + C2C 单聊 + 群/好友事件
    direct_message=True,       # 频道私信
)
print(int(intents))  # 位掩码，可传入 Identify
```

### 类常量

可通过常量直接组合（`Intents.__init__` 的 `value` 逻辑不接受常量，若需自定义可构造后按位或）：

| 常量 | 值 | 对应能力 |
| :--- | :--- | :--- |
| `Intents.GUILDS` | `1 << 0` | 频道事件 |
| `Intents.GUILD_MEMBERS` | `1 << 1` | 频道成员 |
| `Intents.GUILD_MODERATION` | `1 << 2` | 频道管理 |
| `Intents.GUILD_MESSAGES` | `1 << 9` | 频道消息（私域） |
| `Intents.GUILD_MESSAGE_REACTIONS` | `1 << 10` | 频道表情回应 |
| `Intents.DIRECT_MESSAGE` | `1 << 12` | 频道私信 |
| `Intents.GROUP_AND_C2C_EVENT` | `1 << 25` | 群聊 + C2C 单聊 + 群/好友事件 |
| `Intents.INTERACTION` | `1 << 26` | 互动事件 |
| `Intents.MESSAGE_AUDIT` | `1 << 27` | 消息审核 |
| `Intents.FORUMS_EVENT` | `1 << 28` | 论坛事件（私域） |
| `Intents.AUDIO_ACTION` | `1 << 29` | 音频动作 |
| `Intents.PUBLIC_GUILD_MESSAGES` | `1 << 30` | 频道 @ 消息 |

## API

`qqbot_openapi.api.API` — 开放平台 REST API。通过 `client.api` 获取（`start()` 后可用），也可独立构造：`API(HTTPClient(...))`。

### 接口一览

| 方法 | HTTP | 说明 |
| :--- | :--- | :--- |
| `post_group_message` | `POST /v2/groups/{group_openid}/messages` | 群聊消息（文本/Markdown/键盘/富媒体） |
| `post_c2c_message` | `POST /v2/users/{openid}/messages` | 单聊消息（含 `input_notify` 输入中状态） |
| `post_channel_message` | `POST /channels/{channel_id}/messages` | 频道子频道消息 |
| `post_stream_message` | `POST /v2/users/{user_openid}/stream_messages` | 单聊流式消息（AI 流式回复） |
| `post_group_file` | `POST /v2/groups/{group_openid}/files` | 群聊富媒体文件 |
| `post_c2c_file` | `POST /v2/users/{openid}/files` | 单聊富媒体文件 |
| `post_c2c_upload_prepare` | `POST /v2/users/{openid}/upload_prepare` | 单聊分片上传准备 |
| `post_group_upload_prepare` | `POST /v2/groups/{group_openid}/upload_prepare` | 群聊分片上传准备 |
| `post_c2c_upload_part_finish` | `POST /v2/users/{openid}/upload_part_finish` | 单聊分片上报完成 |
| `post_group_upload_part_finish` | `POST /v2/groups/{group_openid}/upload_part_finish` | 群聊分片上报完成 |
| `get_group_info` | `GET /v2/groups/{group_openid}/info` | 群基本信息（白名单） |
| `get_group_bot_state` | `GET /v2/groups/{group_openid}/bot_state` | 机器人群内状态（白名单） |
| `delete_message` | `POST .../messages/{message_id}/recall` | 撤回消息（`post_group_recall` / `post_c2c_recall` 别名） |
| `get_group_restrict_chat_setting` | `GET /v2/groups/{group_openid}/restrict_chat_setting` | 查询群禁言设置 |
| `set_group_restrict_chat_setting` | `POST /v2/groups/{group_openid}/restrict_chat_setting` | 设置群禁言 |
| `get_group_join_request_list` | `GET /v2/groups/{group_openid}/join_requests` | 入群申请列表 |
| `approval_join_request` | `POST /v2/groups/{group_openid}/join_requests/{request_id}` | 审批入群申请 |
| `get_join_approval_strategies` | `GET /v2/groups/join_approval_strategies` | 查询入群自动审批策略 |
| `create_join_approval_strategy` | `POST /v2/groups/join_approval_strategy` | 创建自动审批策略 |
| `delete_join_approval_strategy` | `DELETE /v2/groups/join_approval_strategy/{strategy_id}` | 删除自动审批策略 |
| `update_join_approval_strategy` | `PATCH /v2/groups/join_approval_strategy/{strategy_id}` | 更新自动审批策略 |
| `execute_join_approval_strategy` | `POST /v2/groups/join_approval_strategy/{strategy_id}/execute` | 执行自动审批策略 |
| `update_join_approval_strategy_whitelist` | `POST /v2/groups/join_approval_strategy/{strategy_id}/whitelist` | 更新策略白名单 |

### post_group_message

```python
async def post_group_message(
    self,
    group_openid: str,
    msg_type: int = 0,
    msg_id: str = "",
    msg_seq: Optional[int] = None,
    content: Optional[str] = None,
    markdown: Optional[Union[str, Dict[str, Any]]] = None,
    keyboard: Optional[Dict[str, Any]] = None,
    ark: Optional[Dict[str, Any]] = None,
    message_reference: Optional[Dict[str, Any]] = None,
    msg_elements: Optional[List[Dict[str, Any]]] = None,
    force_verify_image_resource: Optional[bool] = None,
    event_id: str | None = None,
    media: dict[str, Any] | None = None,
    is_wakeup: bool | None = None,
) -> dict[str, Any]
```

发送群聊消息（`POST /v2/groups/{group_openid}/messages`）。

| 参数 | 说明 |
| :--- | :--- |
| `group_openid` | 群标识（群事件/消息中的 `group_openid`） |
| `msg_type` | 消息类型：`0` 文本 / `2` Markdown / `6` 输入中状态 / `7` 富媒体 |
| `msg_id` | 被动回复时传事件消息的 `id`；主动推送留空 `""` |
| `msg_seq` | 主动推送的幂等序号，可选 |
| `content` | 文本内容（`msg_type=0` 时使用） |
| `markdown` | Markdown 内容，可传 `str` 或 `{"content": "..."}` 字典 |
| `keyboard` | 按钮键盘 `Keyboard` 结构 |
| `ark` | ARK 模板消息 |
| `message_reference` | 引用消息（`{"message_id": "..."}`） |
| `msg_elements` | 富媒体消息元素列表 |
| `force_verify_image_resource` | 强制对图片资源进行二次校验，可选 |
| `event_id` | 被动回复事件 ID（防重复回复），可选 |
| `media` | 富媒体文件（`msg_type=7`），结构与分片上传合并后的 `media` 一致 |
| `is_wakeup` | 标记为互动召回消息，可选 |

返回开放平台响应 JSON 字典。

**示例：被动回复**

```python
async def on_group_at_message_create(self, message):
    await self.api.post_group_message(
        group_openid=message.group_openid,
        content="收到 @ 消息！",
        msg_id=message.id,          # 被动回复
    )
```

**示例：主动推送（定时任务）**

```python
await client.api.post_group_message(
    group_openid="GROUP_OPENID",
    content="早上好，今天的任务清单来了～",
    msg_id="",                      # 主动消息
)
```

**示例：Markdown + 键盘**

```python
await client.api.post_group_message(
    group_openid="GROUP_OPENID",
    markdown="## 今日推荐\n- 电影 A\n- 电影 B",
    keyboard={"id": "你的键盘模板 id"},
)
```

### post_c2c_message

```python
async def post_c2c_message(
    self,
    openid: str,
    msg_type: int = 0,
    msg_id: str = "",
    content: Optional[str] = None,
    markdown: Optional[Union[str, Dict[str, Any]]] = None,
    keyboard: Optional[Dict[str, Any]] = None,
    ark: Optional[Dict[str, Any]] = None,
    message_reference: Optional[Dict[str, Any]] = None,
    msg_elements: Optional[List[Dict[str, Any]]] = None,
    force_verify_image_resource: Optional[bool] = None,
    msg_seq: int | None = None,
    event_id: str | None = None,
    media: dict[str, Any] | None = None,
    is_wakeup: bool | None = None,
    input_notify: dict[str, Any] | None = None,
) -> dict[str, Any]
```

发送 C2C 单聊消息（`POST /v2/users/{openid}/messages`）。`openid` 为用户 `user_openid`，其余参数语义同 `post_group_message`。

| 参数 | 说明 |
| :--- | :--- |
| `msg_seq` | 被动回复的递增序号（同一用户回复按 0、1、2、3 递增），用于消息去重；主动推送留空 |
| `event_id` | 被动回复事件 ID（防重复回复），可选 |
| `media` | 富媒体文件（`msg_type=7`） |
| `is_wakeup` | 标记为互动召回消息，可选 |
| `input_notify` | 输入中状态提示（`msg_type=6`，`{"ephemeral": false}`） |

**示例**

```python
async def on_c2c_message_create(self, message):
    # 被动回复：msg_seq 需对同一用户递增（0 → 1 → 2 → 3）
    await self.api.post_c2c_message(
        openid=message.author.user_openid,
        content="私聊收到！",
        msg_id=message.id,
        msg_seq=0,
    )
```

### post_channel_message

```python
async def post_channel_message(
    self,
    channel_id: str,
    msg_type: int = 0,
    msg_id: str = "",
    event_id: Optional[str] = None,
    content: Optional[str] = None,
    markdown: Optional[Union[str, Dict[str, Any]]] = None,
    keyboard: Optional[Dict[str, Any]] = None,
    ark: Optional[Dict[str, Any]] = None,
    message_reference: Optional[Dict[str, Any]] = None,
    msg_elements: Optional[List[Dict[str, Any]]] = None,
    image: Optional[str] = None,
) -> Dict[str, Any]
```

发送频道子频道消息（`POST /channels/{channel_id}/messages`）。用于回复 `AT_MESSAGE_CREATE` / `DIRECT_MESSAGE_CREATE`，`msg_id` 取事件消息的 `id` 即被动回复。

| 参数 | 说明 |
| :--- | :--- |
| `channel_id` | 子频道标识 |
| `event_id` | 事件标识（防重复），可选 |
| `image` | 富媒体图片 URL，可选 |

**示例**

```python
async def on_at_message_create(self, message):
    await self.api.post_channel_message(
        channel_id=message.channel_id,
        content="频道 @ 回复",
        msg_id=message.id,
        image="https://example.com/pic.png",
    )
```

### post_group_file

```python
async def post_group_file(
    self,
    group_openid: str,
    file_type: int,
    url: str = "",
    srv_send_msg: bool = True,
    file_name: str | None = None,
    upload_id: str | None = None,
) -> dict[str, Any]
```

发送群聊富媒体文件（`POST /v2/groups/{group_openid}/files`）。`file_type`：`1` 图片、`2` 视频、`3` 语音，`4` 文件。

`url` 参数会自动检测来源：
- `http(s)://` 开头的公网地址 → 以 `url` 字段上传
- `data:image/png;base64,...` 或纯 base64 字符串 → 以 `file_data` 字段上传

| 参数 | 说明 |
| :--- | :--- |
| `url` | 文件来源（公网地址或 base64），与 `upload_id` 二选一 |
| `srv_send_msg` | 是否同时发送一条文件消息，默认 `True` |
| `file_name` | 文件名，可选 |
| `upload_id` | 分片上传任务 ID（`post_group_upload_prepare` 返回），传此值时走分片合并路径，`url` 可留空 |

`url`、`file_data`、`upload_id` 三者均未提供时抛 `ValueError`。

**示例**

```python
# 公网地址
await client.api.post_group_file(
    group_openid="GROUP_OPENID",
    file_type=1,                       # 图片
    url="https://example.com/pic.png",
    srv_send_msg=False,                # 不主动发送一条消息
)

# base64 数据（data URI 或纯 base64 均可，自动检测）
await client.api.post_group_file(
    group_openid="GROUP_OPENID",
    file_type=1,
    url="data:image/png;base64,iVBORw0KGgoAAAANSUhEUg...",
)
```

### post_c2c_file

```python
async def post_c2c_file(
    self,
    openid: str,
    file_type: int,
    url: str = "",
    srv_send_msg: bool = True,
    file_name: str | None = None,
    upload_id: str | None = None,
) -> dict[str, Any]
```

发送 C2C 单聊富媒体文件（`POST /v2/users/{openid}/files`），参数与来源检测同 `post_group_file`（`url` 字段 or `file_data` 字段）。大文件用 `upload_id` 走分片合并路径。

**示例**

```python
# 公网地址
await client.api.post_c2c_file(
    openid="USER_OPENID",
    file_type=4,                       # 文件
    url="https://example.com/doc.pdf",
)

# base64 数据
await client.api.post_c2c_file(
    openid="USER_OPENID",
    file_type=1,                       # 图片
    url="data:image/jpeg;base64,/9j/4AAQSkZJRgABAQE...",
)
```

### delete_message / post_group_recall / post_c2c_recall

```python
async def delete_message(
    self,
    message_id: str,
    openid: Optional[str] = None,
    group_openid: Optional[str] = None,
) -> Dict[str, Any]
```

撤回消息（`POST /v2/groups/{group_openid}/messages/{message_id}/recall` 或 `/v2/users/{openid}/messages/{message_id}/recall`）。需指定 `group_openid`（群聊）或 `openid`（C2C），两者都缺省时抛 `ValueError`。

`post_group_recall` 与 `post_c2c_recall` 为兼容旧版 botpy 的别名，函数体相同。

**示例**

```python
# 撤回群聊消息（机器人需为管理员）
await client.api.post_group_recall(
    message_id="MESSAGE_ID",
    group_openid="GROUP_OPENID",
)

# 撤回单聊消息
await client.api.post_c2c_recall(
    message_id="MESSAGE_ID",
    openid="USER_OPENID",
)
```

### post_stream_message

```python
async def post_stream_message(
    self,
    user_openid: str,
    input_mode: str | None = None,
    input_state: int | None = None,
    index: int | None = None,
    content_type: str | None = None,
    content_raw: str | None = None,
    event_id: str | None = None,
    msg_id: str | None = None,
    stream_msg_id: str | None = None,
    msg_seq: int | None = None,
    is_wakeup: bool | None = None,
) -> dict[str, Any]
```

单聊流式消息（`POST /v2/users/{user_openid}/stream_messages`），适用于 AI 逐字/逐段输出，上限 50 QPS。同一条回复的每个分片共享同一个 `stream_msg_id`，`index` 从 `0` 递增。

| 参数 | 说明 |
| :--- | :--- |
| `user_openid` | 用户 `openid` |
| `input_mode` | `append`（默认，`content_raw` 在服务端拼接）或 `replace`（全量正文） |
| `input_state` | `1` 生成中，`10` 生成结束 |
| `index` | 分片序号，从 `0` 递增 |
| `content_type` | `text` 或 `markdown` |
| `content_raw` | 本分片正文 |
| `event_id` | 被动回复事件 ID（与 `msg_id` 二选一） |
| `msg_id` | 被动回复的消息 ID（与 `event_id` 二选一） |
| `stream_msg_id` | 流式消息 ID；首片不传，由服务端在响应 `id` 中返回，后续分片必须携带 |
| `msg_seq` | 被动回复递增序号，可选 |
| `is_wakeup` | 标记为互动召回消息，可选 |

**示例**

```python
# 首片：不传 stream_msg_id，从响应中取 id
resp = await client.api.post_stream_message(
    user_openid="USER_OPENID",
    input_state=1,
    index=0,
    content_type="text",
    content_raw="第一段",
    msg_id="MESSAGE_ID",
)
stream_msg_id = resp["id"]

# 后续分片：携带 stream_msg_id，index 递增
await client.api.post_stream_message(
    user_openid="USER_OPENID",
    input_state=1,
    index=1,
    content_raw="第二段",
    stream_msg_id=stream_msg_id,
)

# 收尾：input_state=10 结束
await client.api.post_stream_message(
    user_openid="USER_OPENID",
    input_state=10,
    index=2,
    content_raw="。",
    stream_msg_id=stream_msg_id,
)
```

### 分片上传（大文件富媒体）

官方推荐的大文件上传方式（视频/音频/大图/文件），流程：`upload_prepare` 获取预签名 URL → 逐片 `PUT` → 每片调 `upload_part_finish` 上报 → 全部完成后调 `post_group_file` / `post_c2c_file` 合并发送。

#### post_c2c_upload_prepare

```python
async def post_c2c_upload_prepare(
    self,
    openid: str,
    file_type: int,
    file_size: int | str,
    file_name: str,
    md5: str,
    sha1: str,
    md5_10m: str,
) -> dict[str, Any]
```

单聊上传准备（`POST /v2/users/{openid}/upload_prepare`）。`file_type`：`1` 图片 / `2` 视频 / `3` 语音 / `4` 文件。返回 `upload_id`、`block_size`、`parts`（含各片 `presigned_url`）与 `upload_config`。

#### post_group_upload_prepare

```python
async def post_group_upload_prepare(
    self,
    group_openid: str,
    file_type: int,
    file_size: int | str,
    file_name: str,
    md5: str,
    sha1: str,
    md5_10m: str,
) -> dict[str, Any]
```

群聊上传准备（`POST /v2/groups/{group_openid}/upload_prepare`），参数与返回同 `post_c2c_upload_prepare`。

#### post_c2c_upload_part_finish

```python
async def post_c2c_upload_part_finish(
    self,
    openid: str,
    upload_id: str,
    part_index: int,
    block_size: int | str,
    md5: str,
) -> dict[str, Any]
```

上报单聊某分片已上传完成（`POST /v2/users/{openid}/upload_part_finish`），每片 `PUT` 成功后调用一次。

#### post_group_upload_part_finish

```python
async def post_group_upload_part_finish(
    self,
    group_openid: str,
    upload_id: str,
    part_index: int,
    block_size: int | str,
    md5: str,
) -> dict[str, Any]
```

上报群聊某分片已上传完成（`POST /v2/groups/{group_openid}/upload_part_finish`）。

**完整流程示例（单聊）**

```python
import aiohttp, hashlib

async def upload_file(openid: str, file_type: int, path: str):
    data = open(path, "rb").read()
    md5 = hashlib.md5(data).hexdigest()
    sha1 = hashlib.sha1(data).hexdigest()
    md5_10m = hashlib.md5(data[:10 * 1024 * 1024]).hexdigest()

    resp = await client.api.post_c2c_upload_prepare(
        openid=openid, file_type=file_type, file_size=len(data),
        file_name=path.rsplit("/", 1)[-1],
        md5=md5, sha1=sha1, md5_10m=md5_10m,
    )
    upload_id = resp["upload_id"]
    block_size = int(resp["block_size"])

    async with aiohttp.ClientSession() as session:
        for i, part in enumerate(resp["parts"]):
            chunk = data[i * block_size: (i + 1) * block_size]
            async with session.put(part["presigned_url"], data=chunk) as r:
                r.raise_for_status()
            await client.api.post_c2c_upload_part_finish(
                openid=openid, upload_id=upload_id,
                part_index=i, block_size=len(chunk), md5=md5,
            )

    # 合并发送
    await client.api.post_c2c_file(
        openid=openid, file_type=file_type,
        upload_id=upload_id, file_name="video.mp4",
    )
```

> 注意：`PUT` 分片用原始字节流（`data=chunk`），不要设置 `Content-Type` 之外的额外头部；`block_size` 以实际分片字节数为准。

### get_group_info

```python
async def get_group_info(self, group_openid: str) -> dict[str, Any]
```

获取群基本信息（`GET /v2/groups/{group_openid}/info`）：群名称、简介、分类、标签、成员数量等。需白名单权限（无权限时返回错误码 `11253`）。

```python
info = await client.api.get_group_info(group_openid="GROUP_OPENID")
print(info["name"], info["member_count"])
```

### get_group_bot_state

```python
async def get_group_bot_state(self, group_openid: str) -> dict[str, Any]
```

获取机器人在群内的状态（`GET /v2/groups/{group_openid}/bot_state`）：机器人 `openid`、入群时间、是否接收主动推送、消息接收设置、群成员角色等。需白名单权限。

```python
state = await client.api.get_group_bot_state(group_openid="GROUP_OPENID")
print(state["robot_openid"], state["group_role"])
```

## 消息模型

### Model

`qqbot_openapi.message.Model` — 通用数据模型，由事件/响应字典构造，**字段即属性**，嵌套 dict 自动包装。

**常用方法**

| 方法 | 说明 |
| :--- | :--- |
| `get(name, default=None)` | 取字段值 |
| `to_dict()` | 还原为普通 dict |
| `reply(content=None, markdown=None, **kwargs)` | 回复当前消息，自动分发场景 |
| `__contains__(name)` | 判断字段是否存在（`"content" in message`） |

字段访问缺失时返回 `None`，不会抛异常。

### reply()

```python
async def reply(
    self,
    content: Optional[str] = None,
    markdown: Optional[Union[str, dict]] = None,
    **kwargs,
) -> dict
```

回复当前消息，按消息场景自动分发：

- 有 `group_openid` → `post_group_message`（群聊）
- 有 `channel_id` → `post_channel_message`（频道/私信）
- 有 `author.user_openid` → `post_c2c_message`（单聊）

`markdown` 非空时 `msg_type` 自动置为 `2`。消息对象未绑定 API 时抛 `RuntimeError`（只有事件回调中收到的消息可调用）。

**示例**

```python
async def on_c2c_message_create(self, message):
    await message.reply(content="文本回复")                          # 文本
    await message.reply(markdown="**加粗** 与 `代码`")              # Markdown
    await message.reply(content="回复", keyboard={"id": "KB_ID"})  # 透传 kwargs
```

### Message / GroupMessage / DirectMessage

| 模型 | 对应事件 | 关键字段 |
| :--- | :--- | :--- |
| `Message` | 频道消息（`AT_MESSAGE_CREATE` 等） | `id`, `channel_id`, `author`, `content`, `timestamp` |
| `GroupMessage` | 群聊 / C2C | `id`, `group_openid`, `author`, `content`, `message_type`, `message_scene`, `attachments`, `mentions`, `ark_data`, `msg_elements` |
| `DirectMessage` | 频道私信（`DIRECT_MESSAGE_CREATE`） | `id`, `channel_id`, `author`, `content` |
| `Group` | 群事件 | `group_openid`, `op_member_openid`, `timestamp`, `scene` |
| `FriendUser` | 好友事件 | `openid`, `timestamp`, `scene`, `scene_param`, `author` |
| `Ready` | 就绪事件 | `version`, `session_id`, `user`, `shard` |

**示例：遍历字段**

```python
async def on_group_message_create(self, message):
    # 直接属性访问嵌套字段
    user_openid = message.author.user_openid
    if message.get("content") is None:
        print("纯表情/图片消息")
    if "attachments" in message:
        print("带附件:", message.attachments)
```

## AccessTokenManager

`qqbot_openapi.auth.AccessTokenManager` — 获取并自动刷新 AppAccessToken。首次调用 `get_access_token()` 时向 `/app/getAppAccessToken` 申请，过期前 60s 自动提前刷新。

```python
AccessTokenManager(app_id, secret, base_url=None, timeout=10.0)
```

**示例**

```python
from qqbot_openapi import AccessTokenManager

manager = AccessTokenManager("APPID", "SECRET")
token = await manager.get_access_token()   # 返回有效 token，必要时自动刷新
# 强制刷新
new_token = await manager.refresh()
await manager.close()
```

环境域名常量（`auth.py`）：

| 常量 | 值 |
| :--- | :--- |
| `API_BASE_PROD` | `https://api.bot.qq.com` |
| `WSS_BASE_PROD` | `wss://api.bot.qq.com/websocket` |

## HTTPClient / Route

`qqbot_openapi.http.HTTPClient` — 基于 httpx 的异步 HTTP 客户端，自动注入 `Authorization: QQBot {token}`，收到 401 时刷新 token 重试一次。

```python
HTTPClient(base_url, token_manager, timeout=60.0)
```

`qqbot_openapi.http.Route` — 路径模板，`Route("POST", "/v2/groups/{group_openid}/messages", group_openid=xxx)` 以关键字参数填充占位符。

**示例：自定义 API 请求**

```python
from qqbot_openapi import AccessTokenManager, HTTPClient, Route

manager = AccessTokenManager("APPID", "SECRET")
http = HTTPClient("https://api.bot.qq.com", manager)

data = await http.request(
    Route("GET", "/v2/groups/{group_openid}/messages", group_openid="GROUP_OPENID"),
    params={"limit": 20},
)
print(data)
await http.close()
```

`HTTPClient.request` 在 HTTP >= 400 时抛 `APIError`。

## GatewayClient / ConnectionState

`qqbot_openapi.connection` — WebSocket 网关实现，通常无需直接使用：

- `GatewayClient(wss_url, token_manager, intents, state, shard=[0, 1])`：网关连接与自动重连。`run()` 持续运行，致命关闭码（鉴权失败、无权限等）抛 `WebSocketClosedError`；`stop()` 主动停止。
- `ConnectionState(client)`：维护 `session_id` / `seq`，解析 Dispatch 事件并分发到 `client` 的 `on_xxx` 回调。

## 异常体系

`qqbot_openapi.errors`：

| 异常 | 父类 | 触发场景 |
| :--- | :--- | :--- |
| `QQBotError` | `Exception` | SDK 基础异常 |
| `AccessTokenError` | `QQBotError` | `getAppAccessToken` 获取凭证失败 |
| `APIError` | `QQBotError` | REST API 返回业务错误（属性：`code`、`message`、`request_id`） |
| `GatewayError` | `QQBotError` | 网关连接错误 |
| `WebSocketClosedError` | `GatewayError` | 网关关闭（属性：`code`、`reason`） |
| `NotSupportError` | `QQBotError` | 接口或参数不被支持 |

**示例**

```python
from qqbot_openapi import APIError

try:
    await client.api.post_group_message(group_openid=..., content="hi")
except APIError as exc:
    print(exc.code, exc.message, exc.request_id)
```

## 日志

`qqbot_openapi.logging.get_logger(name=None)` — 返回标准库 `logging.Logger`，缺省命名空间 `qqbot_openapi`。

```python
from qqbot_openapi import get_logger

logger = get_logger("my_bot")
logger.info("机器人启动")
```

## 机器人应用层

项目业务层（`client.py`、`ai/`、`Tools/`、`plugins/`）基于本 SDK 封装，核心入口：

- `XCLRClient`（项目 `client.py`）— 继承 `qqbot_openapi.Client`，加载插件系统并接入 AI 对话、签到、角色等能力。
- 插件开发约定：见「插件开发」文档。