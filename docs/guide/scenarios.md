---
prev:
  text: '项目结构'
  link: '/guide/structure'
next:
  text: '插件开发'
  link: '/plugins/introduction'
---

# 消息场景

机器人支持以下 4 种消息场景：

## QQ 单聊 (C2C_MESSAGE_CREATE)

用户私聊机器人时触发。支持完整功能：
- 内置命令（`ping`、`帮助`、`状态`、`注销`）
- 角色命令（`角色 列表`、`角色 切换`...）
- AI 对话（直接发送消息即可触发）
- `#消息` 格式显式触发 AI 对话

### 对话上下文

单聊中会自动维护每用户的对话上下文（最多 20 条），可通过发送 `注销` 清除。

## QQ 群聊@机器人 (GROUP_AT_MESSAGE_CREATE)

用户在群中 @机器人 时触发。支持：
- 内置命令（`ping`、`帮助`、`状态`）
- 角色命令
- 插件命令（`签到`、`天气 北京`、`ping 1.1.1.1` 等）
- **不支持** AI 对话

命令前缀 `+` 或 `/` 会被自动去除，例如 `+/签到` 等价于 `签到`。

## QQ 群聊全量消息 (GROUP_MESSAGE_CREATE)

群内所有消息（私域机器人可接收）。功能与 @消息 相同，但：
- 自动过滤 @机器人的前缀
- 跳过 `affection` 插件（避免频繁查询）
- 仅 `#` 前缀消息会提示未找到命令

## 频道消息

支持两种频道事件：

| 事件 | 说明 |
| :--- | :--- |
| `DIRECT_MESSAGE_CREATE` | 频道私信，功能类似 QQ 单聊，支持 AI 对话 |
| `AT_MESSAGE_CREATE` | 频道 @机器人，类似群聊@机器人，不支持 AI 对话 |

### 消息处理优先级

```
内置命令 > 角色命令 > 插件命令 > AI 对话(仅限单聊/频道私信)
```

## 事件处理概览

| 客户端方法 | 对应事件 | AI 支持 |
| :--- | :--- | :---: |
| `on_c2c_message_create` | QQ 单聊 | ✅ |
| `on_group_at_message_create` | QQ 群聊@ | ❌ |
| `on_group_message_create` | 群聊全量 | ❌ |
| `on_direct_message_create` | 频道私信 | ✅ |
| `on_at_message_create` | 频道@ | ❌ |
| `on_group_add_robot` | 机器人入群 | — |
| `on_group_del_robot` | 机器人退群 | — |
