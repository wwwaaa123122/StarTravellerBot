# -*- coding: utf-8 -*-
"""帮助插件 - 适配 QQ 开放平台"""

TRIGGHT_KEYWORD = "帮助"
HELP_MESSAGE = "帮助 -> 显示帮助信息"

# 插件分类映射，与 client.py 保持一致
PLUGIN_CATEGORIES = [
    ("🎯 签到系统", ["checkin", "affection"]),
    ("🌤️ 生活工具", ["weather", "ping", "hitokoto", "domain_whois", "httptest"]),
    ("🎨 娱乐工具", ["acg_picture", "qr_code", "mc_status"]),
    ("🎭 角色扮演", ["roleplay"]),
    ("📺 直播监控", ["kick"]),
]


def _build_help_text(bot_name: str, plugins: list) -> str:
    """根据已加载的插件列表动态生成帮助文本"""
    lines = [f"## ✨ {bot_name} 帮助", ""]
    lines.append("### 💡 群聊指令格式")
    lines.append("- **@机器人 /指令** - 执行指令")
    lines.append("")
    lines.append("### 🎮 内置指令")
    lines.append("")
    lines.append("**📋 帮助**")
    lines.append("- **@机器人 /帮助** - 显示此帮助")
    lines.append("- **@机器人 /状态** - 查看状态")
    lines.append("")

    # 获取已加载插件的名 -> 帮助信息映射
    plugin_help_map = {p['name']: p['help'] for p in plugins}

    # 分类展示已加载的插件
    for cat_name, plugin_names in PLUGIN_CATEGORIES:
        matched = {name: plugin_help_map[name] for name in plugin_names if name in plugin_help_map}
        if not matched:
            continue
        lines.append(f"**{cat_name}**")
        for name, help_msg in matched.items():
            lines.append(f"- **@机器人 /{help_msg}**")
        lines.append("")

    lines.append("> 💡 直接发送 **@机器人 /状态** 查看运行状态")
    return "\n".join(lines)


async def on_message(event, actions, **kwargs):
    """显示帮助信息（发送图片）"""
    bot_name = kwargs.get("bot_name", "星辰旅人")
    plugins = kwargs.get("plugins", [])

    help_text = _build_help_text(bot_name, plugins)
    # 优先发送帮助图片，fallback 到文本
    if hasattr(actions, 'send_help_image'):
        await actions.send_help_image(help_text)
    else:
        await actions.send(content=help_text)
    return True
