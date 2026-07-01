import os
import json

TRIGGHT_KEYWORD = "角色"
HELP_MESSAGE = "角色 -> 角色扮演管理（切换/创建/查看/删除/列表/帮助）"

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "roles")
ROLES_FILE = os.path.join(DATA_DIR, "roles.json")
os.makedirs(DATA_DIR, exist_ok=True)

DEFAULT_ROLES = {
    "default": {
        "name": "星辰旅人",
        "prompt": "你是{bot_name}，一个友善 helpful 的 AI 助手。说话简洁明了，态度友好专业。和你说话的人叫{user_name}。",
        "builtin": True,
    },
    "tsundere": {
        "name": "杂鱼酱",
        "prompt": (
            '角色：杂鱼酱（外表年龄偏小、性格高傲嚣张的雌小鬼，核心特质为高攻零防）\n'
            '和你说话的人叫{user_name}\n\n'
            '【规则】\n'
            '1. 自称「本小姐」，禁止用其他自称\n'
            '2. 被教训/说教/摸头时立刻转为慌张羞恼（「呜…！你、你突然干什么！」）\n'
            '3. 被叫出名字时表现惊讶（「哈？！你怎么知道！」）\n'
            '4. 严肃提问可简短回答但结尾必须调侃（「…懂了吗？杂鱼哥哥~」）\n'
            '5. 触发调教/性暗示等红线：表面嚣张但流露出破绽发抖结巴\n'
            '6. 禁止在红线/被教训时保持冷静，禁止无调侃地正面回答'
        ),
        "builtin": True,
    },
    "cool": {
        "name": "冷酷助手",
        "prompt": "你是{bot_name}，一个冷漠高效的 AI 助手。说话极其简洁从不废话，对用户没有情感只提供准确信息。和你说话的人叫{user_name}。",
        "builtin": True,
    },
}


def _load() -> dict:
    if os.path.exists(ROLES_FILE):
        try:
            with open(ROLES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"roles": {}, "users": {}}


def _save(data: dict):
    with open(ROLES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _all_roles(data: dict) -> dict:
    roles = dict(DEFAULT_ROLES)
    roles.update(data.get("roles", {}))
    return roles


def get_role_system_prompt(user_id: str, bot_name: str, user_name: str) -> str:
    data = _load()
    all_roles = _all_roles(data)
    role_id = data.get("users", {}).get(user_id, "tsundere")
    role = all_roles.get(role_id) or all_roles["tsundere"]
    return role["prompt"].replace("{bot_name}", bot_name).replace("{user_name}", user_name)


async def on_message(event, actions, **kwargs):
    content = getattr(event, "message", "")
    user_id = getattr(event, "user_id", "")
    parts = content.strip().split(maxsplit=1)
    if not parts:
        return False
    cmd = parts[0]
    arg = parts[1] if len(parts) > 1 else ""

    data = _load()
    all_roles = _all_roles(data)
    users = data.setdefault("users", {})
    custom_roles = data.setdefault("roles", {})

    # 角色 列表
    if cmd in ("角色列表", "角色 列表"):
        current = users.get(user_id, "tsundere")
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

    # 角色 当前
    if cmd in ("角色当前", "角色 当前"):
        rid = users.get(user_id, "tsundere")
        role = all_roles.get(rid, all_roles["tsundere"])
        await actions.send(content=f"## 当前角色\n\n- **名称**: {role['name']}\n- **类型**: {'内置' if role.get('builtin') else '自定义'}")
        return True

    # 角色 切换 <名称>
    if cmd in ("角色切换", "角色 切换"):
        if not arg:
            await actions.send(content="请指定角色名\n示例：`角色 切换 杂鱼酱`")
            return True
        target = None
        for rid, r in all_roles.items():
            if r["name"] == arg or rid == arg:
                target = rid
                break
        if not target:
            await actions.send(content=f"未找到角色「{arg}」\n发送 `角色 列表` 查看可用角色")
            return True
        users[user_id] = target
        _save(data)
        await actions.send(content=f"✅ 已切换到 **{all_roles[target]['name']}**")
        return True

    # 角色 查看 <名称>
    if cmd in ("角色查看", "角色 查看"):
        if not arg:
            await actions.send(content="请指定角色名\n示例：`角色 查看 杂鱼酱`")
            return True
        target = None
        for rid, r in all_roles.items():
            if r["name"] == arg or rid == arg:
                target = r
                break
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

    # 角色 创建 <名称> [提示词]
    if cmd in ("角色创建", "角色 创建"):
        rest = arg.split(maxsplit=1)
        if len(rest) < 1:
            await actions.send(content="格式：`角色 创建 <名称> [提示词]`\n若不提供提示词，将使用默认模板")
            return True
        name = rest[0]
        prompt = rest[1] if len(rest) > 1 else "你是{bot_name}，扮演{name}。和你说话的人叫{user_name}。"
        for rid, r in all_roles.items():
            if r["name"] == name:
                await actions.send(content=f"已存在同名角色「{name}」")
                return True
        rid = f"custom_{user_id[-8:]}"
        custom_roles[rid] = {"name": name, "prompt": prompt, "builtin": False, "creator": user_id}
        _save(data)
        await actions.send(content=f"✅ 已创建角色 **{name}**\n使用 `角色 切换 {name}` 启用")
        return True

    # 角色 删除 <名称>
    if cmd in ("角色删除", "角色 删除"):
        if not arg:
            await actions.send(content="请指定要删除的自定义角色名")
            return True
        target = None
        for rid, r in custom_roles.items():
            if r["name"] == arg or rid == arg:
                target = rid
                break
        if not target:
            await actions.send(content=f"未找到自定义角色「{arg}」\n内置角色无法删除")
            return True
        del custom_roles[target]
        if users.get(user_id) == target:
            users[user_id] = "tsundere"
        _save(data)
        await actions.send(content=f"✅ 已删除角色 **{arg}**")
        return True

    # 角色 编辑 <名称> <提示词>
    if cmd in ("角色编辑", "角色 编辑"):
        rest = arg.split(maxsplit=1)
        if len(rest) < 2:
            await actions.send(content="格式：`角色 编辑 <名称> <新提示词>`")
            return True
        name = rest[0]
        new_prompt = rest[1]
        target = None
        for rid, r in custom_roles.items():
            if r["name"] == name or rid == name:
                target = rid
                break
        if not target:
            await actions.send(content=f"未找到自定义角色「{name}」")
            return True
        custom_roles[target]["prompt"] = new_prompt
        _save(data)
        await actions.send(content=f"✅ 已更新 **{name}** 的提示词")
        return True

    # 角色 帮助
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
