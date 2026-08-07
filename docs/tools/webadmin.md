---
prev:
  text: '工具概述'
  link: '/tools/overview'
next:
  text: 'API 参考'
  link: '/api/reference'
---

# Web 管理后台

StarTraveller 提供一个独立于机器人主进程的 Web 管理后台（`webadmin/`），用于在浏览器中查看系统状态、管理用户与插件。它基于 Flask 构建，按需读取机器人的数据文件，不修改 `client.py` / `main.py` 的运行逻辑。

## 功能总览

| 页面 | 功能 |
| :--- | :--- |
| 仪表盘 | 系统概览：用户数、今日签到、积分总量、角色分布、近 14 天签到趋势、访问统计、机器人运行状态 |
| 用户管理 | 查看全部用户（昵称 / 积分 / 连续签到 / 好感度 / 角色），支持搜索与排序 |
| 记忆库 | 检索所有用户的 RAG 对话记忆记录 |
| 插件管理 | 展示已加载插件列表及其触发关键字、帮助信息 |
| 定时任务 | 查看定时群发配置（启用状态 / 发送时间 / 目标频道 / 最近发送日期） |
| 系统设置 | 查看机器人配置（脱敏展示密钥类字段）与运行信息 |

## 启动方式

### 随机器人自动启动

在 `config.json` 中配置 `webadmin` 段后，`main.py` 会以**守护线程**方式随机器人同步启动管理后台，不影响机器人事件循环：

```json
{
  "webadmin": {
    "enabled": true,
    "host": "0.0.0.0",
    "port": 8765,
    "password": "你的强密码"
  }
}
```

### 独立启动

```bash
python -m webadmin.server --host 0.0.0.0 --port 8765
```

### 配置优先级

1. 启动参数（`--host` / `--port` / `--password`）
2. 环境变量 `STAR_TRAVELLER_ADMIN_HOST` / `_PORT` / `_PASSWORD`
3. `config.json` 的 `webadmin` 段
4. 内置默认值（`0.0.0.0:8765`，密码 `admin123`）

> **安全提示**：默认监听 `0.0.0.0`（所有网卡），访问时不校验 Host 头端口，请务必设置强密码，避免使用默认密码 `admin123`。

## 访问与登录

启动后访问 `http://服务器IP:8765/admin`，输入密码即可登录。Token 有效期 7 天，登录接口带速率限制（1 分钟内的失败尝试）。

## 界面预览

### 仪表盘

![仪表盘](/webadmin/dashboard.webp)

仪表盘集中展示机器人运行的核心指标：用户总数、今日签到人数、累计积分、角色数量、RAG 记忆条数、插件数量与访问统计，并绘制近 14 天签到趋势与角色分布图。

### 用户管理

![用户管理](/webadmin/users.webp)

用户管理页列出所有签到用户，展示昵称、积分、连续签到天数、好感度与当前角色，支持关键字搜索。

![用户核验](/webadmin/users-verify.webp)

支持对用户进行核验操作，便于管理群成员状态。

### 系统设置

![系统设置](/webadmin/settings-dark.webp)

系统设置页展示机器人配置与运行信息，密钥类字段（密码、Secret、Token、AppID 等）自动脱敏显示，避免敏感信息泄露。

### 响应式布局

管理后台适配桌面端与移动端：

![移动端抽屉菜单](/webadmin/mobile-drawer.webp)

![桌面端侧边栏折叠](/webadmin/sidebar-collapsed.webp)

## API 端点

| 方法 | 路径 | 说明 |
| :--- | :--- | :--- |
| POST | `/admin/api/login` | 登录，body `{"password": "..."}`，返回 Token |
| GET | `/admin/api/ping` | 存活检测 |
| GET | `/admin/api/overview` | 仪表盘数据 |
| GET | `/admin/api/status` | 系统状态（CPU / 内存 / 磁盘 / 开机时长） |
| GET | `/admin/api/users` | 用户列表 |
| GET | `/admin/api/memory` | RAG 记忆记录 |
| GET | `/admin/api/plugins` | 插件列表 |
| GET | `/admin/api/schedule` | 定时任务配置 |
| GET | `/admin/api/config` | 机器人配置（脱敏） |

除 `login` 与 `ping` 外的接口均需携带请求头 `Authorization: Bearer <token>`。
