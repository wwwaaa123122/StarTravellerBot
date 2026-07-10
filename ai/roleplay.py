import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ai.role_manager import RoleManager

TRIGGHT_KEYWORD = "角色"
HELP_MESSAGE = "角色 -> 角色扮演管理（切换/创建/查看/删除/列表/帮助）"

_role_manager = None


def _get_manager():
    global _role_manager
    if _role_manager is None:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "roles")
        _role_manager = RoleManager(data_dir)
    return _role_manager


async def on_message(event, actions, **kwargs):
    content = getattr(event, "message", "")
    user_id = getattr(event, "user_id", "")
    parts = content.strip().split(maxsplit=1)
    if not parts:
        return False
    cmd = parts[0]
    arg = parts[1] if len(parts) > 1 else ""

    rm = _get_manager()

    if cmd in ("角色列表", "角色 列表"):
        all_roles = rm.get_all_roles()
        current = rm.get_user_role_id(user_id)
        lines = ["## 🎭 可用角色", ""]
        for rid, r in all_roles.items():
            mark = "✅" if rid == current else "  "
            tag = "📌" if r.get("builtin") else "✏️"
            lines.append(f"- {mark} {tag} **{r['name']}**")
        lines += [
            "",
            "### 命令",
            "- `角色 切换 <名称>` - 切换角色",
            "- `角色 查看 <名称>` - 查看详情",
            "- `角色 创建 <名称> <提示词>` - 创建自定义角色",
            "- `角色 删除 <名称>` - 删除自定义角色",
            "- `角色 当前` - 查看当前角色",
            "- `角色 帮助` - 详细帮助",
        ]
        await actions.send(content="\n".join(lines))
        return True

    if cmd in ("角色当前", "角色 当前"):
        rid = rm.get_user_role_id(user_id)
        all_roles = rm.get_all_roles()
        role = all_roles.get(rid)
        if not role:
            role = {"name": "未知", "builtin": False}
        await actions.send(content=f"## 当前角色\n\n- **名称**: {role['name']}\n- **类型**: {'内置' if role.get('builtin') else '自定义'}")
        return True

    if cmd in ("角色切换", "角色 切换"):
        if not arg:
            await actions.send(content="请指定角色名\n示例：`角色 切换 杂鱼酱`")
            return True
        target_id, target_role = rm.find_role(arg)
        if not target_role:
            await actions.send(content=f"未找到角色「{arg}」\n发送 `角色 列表` 查看可用角色")
            return True
        rm.set_user_role(user_id, target_id)
        await actions.send(content=f"✅ 已切换到 **{target_role['name']}**")
        return True

    if cmd in ("角色查看", "角色 查看"):
        if not arg:
            await actions.send(content="请指定角色名\n示例：`角色 查看 杂鱼酱`")
            return True
        _, target = rm.find_role(arg)
        if not target:
            await actions.send(content=f"未找到角色「{arg}」")
            return True
        preview = target["prompt"][:200]
        await actions.send(content=(
            f"## 🎭 {target['name']}\n\n"
            f"- **类型**: {'内置' if target.get('builtin') else '自定义'}\n"
            f"\n> 📜 **提示词预览**:\n> {preview}..."
        ))
        return True

    if cmd in ("角色创建", "角色 创建"):
        rest = arg.split(maxsplit=1)
        if len(rest) < 1:
            await actions.send(content="格式：`角色 创建 <名称> [提示词]`\n若不提供提示词，将使用默认模板")
            return True
        name = rest[0]
        prompt = rest[1] if len(rest) > 1 else "你是{bot_name}，扮演{name}。和你说话的人叫{user_name}。"
        if rm.create_role(name, prompt, user_id):
            await actions.send(content=f"✅ 已创建角色 **{name}**\n使用 `角色 切换 {name}` 启用")
        else:
            await actions.send(content=f"已存在同名角色「{name}」")
        return True

    if cmd in ("角色删除", "角色 删除"):
        if not arg:
            await actions.send(content="请指定要删除的自定义角色名")
            return True
        _, target = rm.find_custom_role(arg)
        if not target:
            await actions.send(content=f"未找到自定义角色「{arg}」\n内置角色无法删除")
            return True
        rm.delete_role(arg)
        await actions.send(content=f"✅ 已删除角色 **{arg}**")
        return True

    if cmd in ("角色编辑", "角色 编辑"):
        rest = arg.split(maxsplit=1)
        if len(rest) < 2:
            await actions.send(content="格式：`角色 编辑 <名称> <新提示词>`")
            return True
        name = rest[0]
        new_prompt = rest[1]
        if rm.edit_role(name, new_prompt):
            await actions.send(content=f"✅ 已更新 **{name}** 的提示词")
        else:
            await actions.send(content=f"未找到自定义角色「{name}」")
        return True

    if cmd in ("角色帮助", "角色 帮助"):
        await actions.send(content=(
            "## 🎭 角色扮演帮助\n\n"
            "### 命令\n"
            "- `角色 列表` - 查看所有角色\n"
            "- `角色 当前` - 查看当前角色\n"
            "- `角色 切换 <名称>` - 切换角色\n"
            "- `角色 查看 <名称>` - 查看角色详情\n"
            "- `角色 创建 <名称> [提示词]` - 创建自定义角色\n"
            "- `角色 编辑 <名称> <新提示词>` - 编辑自定义角色提示词\n"
            "- `角色 删除 <名称>` - 删除自定义角色\n\n"
            "> 提示词中可用 `{bot_name}` `{user_name}` `{name}` 变量"
        ))
        return True

    return False
