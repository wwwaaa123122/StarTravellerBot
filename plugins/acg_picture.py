import time as _time

TRIGGHT_KEYWORD = "生图 ACG "
HELP_MESSAGE = "生图 ACG (任意类型) -> 制作精美二次元壁纸 (发送 `@机器人 生图 ACG 帮助` 查看帮助菜单)"

_cooldowns: dict = {}

API_URLS = {
    "随机": "https://www.loliapi.com/acg/",
    "电脑壁纸": "https://www.loliapi.com/acg/pc/",
    "手机壁纸": "https://www.loliapi.com/acg/pe/",
    "头像": "https://www.loliapi.com/acg/pp/",
    "背景": "https://www.loliapi.com/bg/",
}


async def on_message(event, actions, **kwargs):
    order = kwargs.get('order', '')
    user_id = event.user_id
    now = _time.time()
    bot_name = kwargs.get('bot_name', '机器人')

    start = order.find("生图 ACG ")
    if start == -1:
        return False
    result = order[start + len("生图 ACG "):].strip()

    # 帮助
    if "帮助" in result:
        lines = [f"### ✨ {bot_name} ACG 壁纸生成"]
        for k in API_URLS:
            lines.append(f"- **{k}**")
        lines.append("")
        lines.append(f"💡 示例：`@机器人 生图 ACG 随机`")
        await actions.send(content="\n".join(lines))
        return True

    # 检查类型
    matched_type = None
    for t in API_URLS:
        if t in result:
            matched_type = t
            break

    if not matched_type:
        lines = [f"### ❌ 类型 `{result}` 不存在", ""]
        lines.append(f"支持的类型：")
        for k in API_URLS:
            lines.append(f"- **{k}**")
        await actions.send(content="\n".join(lines))
        return True

    # 冷却检查
    root_users = kwargs.get('ROOT_User', [])
    is_super = str(user_id) in root_users

    if not is_super and user_id in _cooldowns and now - _cooldowns[user_id] < 18:
        remaining = 18 - (now - _cooldowns[user_id])
        await actions.send(content=f"⏳ 18秒冷却中，请等待 **{remaining:.1f}** 秒")
        return True

    # 发送图片
    api_url = API_URLS[matched_type]
    _cooldowns[user_id] = now

    try:
        await actions.send_file(api_url)
    except Exception as e:
        await actions.send(content=f"❌ 生成失败：{e}")

    return True
