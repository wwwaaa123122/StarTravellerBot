import httpx
import logging
_logger = logging.getLogger("hitokoto")
import logging

TRIGGHT_KEYWORD = "一言"
HELP_MESSAGE = "一言 -> 找一句好听的名言👍"


async def on_message(event, actions, **kwargs):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://international.v1.hitokoto.cn/")
            data = await resp.json()
            txt = f"「{data['hitokoto']}」\n\n—— *{data.get('from_who', '佚名')}*, {data.get('from', '未知出处')}"
    except Exception:
        _logger.warning("一言 API 请求失败", exc_info=True)
        bot_name = kwargs.get('bot_name', '机器人')
        txt = f"请求失败 - {bot_name}"

    await actions.send(content=txt)
    return True
