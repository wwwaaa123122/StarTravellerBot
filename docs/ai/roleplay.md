---
prev:
  text: 'AI 对话'
  link: '/ai/chat'
next:
  text: '工具模块'
  link: '/tools/overview'
---

# 角色系统

## 概述

角色系统允许用户切换不同的 AI 对话角色，每个角色有独立的 system prompt 定义。支持内置角色和用户自定义角色。

由 `RoleManager` 类管理（`ai/role_manager.py`），角色数据持久化在 `data/roles/roles.json`。

## 内置角色

| 角色 | 名称 | 风格 |
| :--- | :--- | :--- |
| `default` | 星辰旅人 | 友善专业的 AI 助手，简洁友好 |
| `tsundere` | 杂鱼酱 | 高傲嚣张的雌小鬼，高攻零防 |
| `cool` | 冷酷助手 | 冷漠高效，极其简洁，不带情感 |

默认角色为 **tsundere**（傲娇）。

## 命令

所有命令通过 `角色` 关键字触发：

| 命令 | 说明 |
| :--- | :--- |
| `角色 列表` | 查看所有可用角色 |
| `角色 当前` | 查看当前使用的角色 |
| `角色 切换 <名称>` | 切换到指定角色 |
| `角色 查看 <名称>` | 查看角色提示词详情 |
| `角色 创建 <名称> [提示词]` | 创建自定义角色 |
| `角色 编辑 <名称> <新提示词>` | 编辑自定义角色提示词 |
| `角色 删除 <名称>` | 删除自定义角色 |
| `角色 帮助` | 查看详细帮助 |

## 自定义角色

创建自定义角色时，提示词中可使用以下变量：

| 变量 | 说明 |
| :--- | :--- |
| `{bot_name}` | 机器人名称（如"星辰旅人"） |
| `{user_name}` | 用户名称 |
| `{self.username}` | 机器人用户名 |

示例：
```
角色 创建 猫娘 你是{bot_name}，一只可爱的猫娘。喜欢撒娇和玩耍。和你说话的人叫{user_name}。
```

### 自定义角色管理

- 自定义角色由创建者管理
- 删除角色时，使用该角色的用户会自动切换到默认角色（tsundere）
- 内置角色不可删除或编辑

## 代码参考

```python
class RoleManager:
    def get_system_prompt(self, user_id, bot_name, user_name, self_username="") -> str:
        """获取用户的 system prompt（变量替换后）"""

    def set_user_role(self, user_id, role_id):
        """设置用户的角色"""

    def get_all_roles(self) -> dict:
        """获取所有角色（内置+自定义）"""

    def create_role(self, name, prompt, creator) -> bool:
        """创建自定义角色，返回是否成功"""

    def delete_role(self, name_or_id) -> bool:
        """删除自定义角色"""

    def edit_role(self, name_or_id, new_prompt) -> bool:
        """编辑自定义角色的提示词"""
```
