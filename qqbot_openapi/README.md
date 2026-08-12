# qqbot-openapi

QQ 开放平台机器人轻量 SDK。覆盖单聊（C2C）、群聊、QQ 频道三种场景的鉴权、WebSocket 网关与 REST API，无重依赖（仅 `httpx` / `aiohttp`）。

## 特性

- **三场景消息**：单聊、群聊 @、频道私信 / 频道 @，`message.reply()` 自动路由
- **完整网关**：WebSocket 自动重连、心跳保活、鉴权失败识别、事件自动分发给 `on_xxx` 回调
- **主动推送**：`msg_seq` 幂等、`is_wakeup` 互动召回、定时群发
- **AI 友好**：单聊流式消息（`post_stream_message`），支持逐段输出
- **富媒体**：文件直传（URL / base64）与官方分片上传（大视频 / 大图）
- **群管理**：群禁言、入群申请审批、自动审批策略（CRUD + 白名单）、群信息查询
- **省心**：token 自动刷新（过期前 60s）、401 自动重试、异常体系清晰

## 安装

```bash
pip install qqbot-openapi
```

本地开发：

```bash
pip install -e .
```

## 快速开始

```python
import asyncio

from qqbot_openapi import Client, Intents

intents = Intents(
    public_guild_messages=True,   # 频道 @ 消息
    public_messages=True,         # 群聊 + C2C + 群/好友事件
    direct_message=True,          # 频道私信
)


class MyBot(Client):
    async def on_ready(self, event):
        print("机器人就绪:", event.user)

    async def on_c2c_message_create(self, message):
        await message.reply(content="你好！")

    async def on_group_at_message_create(self, message):
        await message.reply(content=f"收到 @，来自 {message.author.user_openid}")


client = MyBot(intents=intents)
client.run(appid="你的 AppID", secret="你的 AppSecret")  # 阻塞运行
```

或异步启动：

```python
async def main():
    client = MyBot(intents=intents)
    await client.start(appid="...", secret="...")
    await asyncio.Future()  # 常驻

asyncio.run(main())
```

## 消息收发

`message.reply(...)` 按场景自动路由（群聊 / C2C / 频道），支持文本与 Markdown：

```python
await message.reply(content="文本回复")
await message.reply(markdown="**加粗** 与 `代码`")
await message.reply(content="回复", keyboard={"id": "键盘模板 ID"})  # 透传 kwargs
```

底层 REST 接口（`client.api`）：

| 方法 | 用途 |
| :--- | :--- |
| `post_group_message` / `post_c2c_message` / `post_channel_message` | 群聊 / 单聊 / 频道发消息 |
| `post_stream_message` | 单聊流式消息（AI 逐段输出） |
| `post_group_file` / `post_c2c_file` | 发送文件 / 图片 / 视频 / 语音 |
| `post_c2c_upload_prepare` / `post_group_upload_prepare` | 分片上传准备（获取预签名 URL） |
| `post_c2c_upload_part_finish` / `post_group_upload_part_finish` | 上报分片上传完成 |
| `get_group_info` / `get_group_bot_state` | 群基本信息 / 机器人群内状态（白名单） |
| `delete_message` | 撤回消息（`post_group_recall` / `post_c2c_recall` 别名） |
| 群禁言 / 入群审批 / 自动审批策略系列 | 群管理能力 |

### 流式消息示例

```python
resp = await client.api.post_stream_message(
    user_openid="USER_OPENID", input_state=1, index=0,
    content_type="text", content_raw="第一段", msg_id="MSG_ID",
)
stream_msg_id = resp["id"]   # 首片返回，后续分片携带

await client.api.post_stream_message(
    user_openid="USER_OPENID", input_state=1, index=1,
    content_raw="第二段", stream_msg_id=stream_msg_id,
)
await client.api.post_stream_message(
    user_openid="USER_OPENID", input_state=10, index=2,
    content_raw="。", stream_msg_id=stream_msg_id,
)  # input_state=10 结束
```

### 分片上传

```python
# 1) 准备：拿到 upload_id、block_size、parts（含各片 presigned_url）
resp = await client.api.post_group_upload_prepare(
    group_openid="GROUP_OPENID", file_type=2, file_size=len(data),
    file_name="video.mp4", md5=md5, sha1=sha1, md5_10m=md5_10m,
)
# 2) 逐片 PUT 到 parts[i].presigned_url
# 3) 每片 PUT 成功后上报完成
await client.api.post_group_upload_part_finish(
    group_openid="GROUP_OPENID", upload_id=resp["upload_id"],
    part_index=0, block_size=len(chunk), md5=md5,
)
# 4) 全部完成后合并发送
await client.api.post_group_file(
    group_openid="GROUP_OPENID", file_type=2,
    upload_id=resp["upload_id"], file_name="video.mp4",
)
```

## 事件

在 `Client` 子类中定义 `on_xxx` 即可接收对应事件：

| 回调 | 事件 | 说明 |
| :--- | :--- | :--- |
| `on_ready` | `READY` | 网关就绪 |
| `on_c2c_message_create` | `C2C_MESSAGE_CREATE` | 单聊消息 |
| `on_group_at_message_create` | `GROUP_AT_MESSAGE_CREATE` | 群聊 @ 消息 |
| `on_group_message_create` | `GROUP_MESSAGE_CREATE` | 群聊全量消息 |
| `on_at_message_create` | `AT_MESSAGE_CREATE` | 频道 @ 消息 |
| `on_direct_message_create` | `DIRECT_MESSAGE_CREATE` | 频道私信 |
| `on_group_add_robot` / `on_group_del_robot` | `GROUP_ADD_ROBOT` / `GROUP_DEL_ROBOT` | 机器人入群 / 被移出 |
| `on_group_msg_reject` / `on_group_msg_receive` | `GROUP_MSG_REJECT` / `GROUP_MSG_RECEIVE` | 群内消息权限关闭 / 开启 |
| `on_c2c_msg_receive` / `on_c2c_msg_reject` | `C2C_MSG_RECEIVE` / `C2C_MSG_REJECT` | 用户开启 / 关闭主动消息 |
| `on_subscribe_message_status` | `SUBSCRIBE_MESSAGE_STATUS` | 订阅授权状态变更 |
| `on_friend_add` / `on_friend_del` | `FRIEND_ADD` / `FRIEND_DEL` | 好友添加 / 删除 |

完整列表与 API 参考见仓库文档 `docs/api/reference.md`。

## 进阶

**错误处理**

```python
from qqbot_openapi import APIError

try:
    await client.api.post_group_message(group_openid=..., content="hi")
except APIError as exc:
    print(exc.code, exc.message, exc.request_id)
```

**日志**

```python
from qqbot_openapi import get_logger

logger = get_logger("my_bot")
```

**自定义 HTTP 请求**

```python
from qqbot_openapi import AccessTokenManager, HTTPClient, Route

manager = AccessTokenManager("APPID", "SECRET")
http = HTTPClient("https://api.bot.qq.com", manager)
data = await http.request(
    Route("GET", "/v2/groups/{group_openid}/messages", group_openid="..."),
    params={"limit": 20},
)
```

## 依赖

- `httpx` — REST 请求
- `aiohttp` — 网关 WebSocket

兼容 Python 3.8+。

## 文档

- API 参考：`docs/api/reference.md`
- 消息场景：`docs/guide/scenarios.md`

## License

MIT
