import re
import aiohttp

TRIGGHT_KEYWORD = "Any"
HELP_MESSAGE = "mc状态 <服务器地址> -> 查询 MC 服务器状态"

DOMAIN = re.compile(r"^(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}|(?:\d{1,3}\.){3}\d{1,3})(?::\d+)?$")
KEYWORDS = ["mc状态", "我的世界状态", "minecraft状态", "jv状态"]


async def on_message(event, actions, **kwargs):
    msg = event.message.strip() if hasattr(event, 'message') else ''
    if not msg:
        return False

    msg_lower = msg.lower()
    if not any(kw.lower() in msg_lower for kw in KEYWORDS):
        return False

    for kw in KEYWORDS:
        msg = msg_lower.replace(kw.lower(), "")
    address = msg.strip()

    if not address:
        await actions.send(content="请输入正确的域名或 IP，支持带端口号")
        return True

    if not (DOMAIN.match(address)):
        await actions.send(content="请输入正确的域名或 IP，支持带端口号")
        return True

    url = f"https://api.mcstatus.io/v2/status/java/{address}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    await actions.send(content="网络请求失败")
                    return True
                data = await resp.json()
    except Exception as e:
        await actions.send(content=f"发生错误：{e}")
        return True

    if not data.get("online"):
        await actions.send(content=f"### 服务器状态\n\n- **地址**: `{address}`\n- **状态**: 🔴 离线")
        return True

    lines = [f"### ⛏️ MC 服务器状态", ""]
    lines.append(f"- **地址**: `{address}`")
    lines.append(f"- **状态**: 🟢 在线")

    eula = data.get("eula_blocked")
    if eula is True:
        lines.append("- **正版验证**: ✅ 开启")
    elif eula is False:
        lines.append("- **正版验证**: ❌ 关闭")
    else:
        lines.append("- **正版验证**: ⚠️ 未知")

    lines.append(f"- **版本**: {data['version']['name_clean']}")
    lines.append(f"- **介绍**: {data['motd']['clean'].replace(' ', '')}")
    lines.append(f"- **在线玩家**: {data['players']['online']} / {data['players']['max']}")

    await actions.send(content="\n".join(lines))
    return True
