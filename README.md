# 星辰旅人 - QQ 开放平台机器人

基于 [qq-botpy](https://github.com/tencent-connect/botpy) 的 QQ 开放平台机器人实现。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

编辑 `open-qq/.env` 文件：

```env
AppID=你的AppID
AppSecret=你的AppSecret
```

### 3. 运行

```bash
python open-qq/main.py
```

## 支持的场景

| 场景 | 事件类型 | 说明 |
|------|----------|------|
| QQ 单聊 | C2C_MESSAGE_CREATE | 用户与机器人单独对话 |
| QQ 群聊@机器人 | GROUP_AT_MESSAGE_CREATE | 用户在群内@机器人 |
| 频道私信 | DIRECT_MESSAGE_CREATE | 用户在频道私信机器人 |
| 频道@机器人 | AT_MESSAGE_CREATE | 用户在频道@机器人 |

## 消息类型

| 类型 | 代码 | 说明 |
|------|------|------|
| 文本 | 0 | 普通文本消息 |
| Markdown | 2 | Markdown 格式消息 |
| Ark | 3 | 卡片消息 |
| Embed | 4 | 嵌入式消息 |
| 富媒体 | 7 | 图片、视频等 |

## 命令列表

- `帮助` - 显示帮助信息
- `状态` - 查看机器人状态
- `ping` - 测试机器人响应
- `# [问题]` - 与 AI 对话

## 注意事项

1. **被动消息限制**: 
   - 群聊: 5 分钟内有效，每个消息最多回复 5 次
   - 单聊: 60 分钟内有效，每个消息最多回复 5 次

2. **主动消息限制**:
   - 单聊/群聊: 每月 4 条
   - 频道: 每天每子频道 20 条

3. **频率限制**:
   - 频道: 每秒最多 5 条消息

## 文档

- [QQ 开放平台文档](https://bot.q.qq.com/wiki/)
- [botpy 文档](https://bot.q.qq.com/wiki/develop/pythonsdk/)
- [API 参考](https://bot.q.qq.com/wiki/develop/api-v2/)
