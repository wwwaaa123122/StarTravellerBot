import aiohttp

TRIGGHT_KEYWORD = "转码 "
HELP_MESSAGE = "转码 <url/文本> -> 生成二维码图片"

HEADERS = {"User-Agent": "xiaoxiaoapi/1.0.0 (https://xxapi.cn)"}
API_URL = "https://v2.xxapi.cn/api/qrcode"


async def on_message(event, actions, **kwargs):
    order = kwargs.get('order', '')
    start = order.find("转码 ")
    if start == -1:
        return False
    text = order[start + len("转码 "):].strip()

    if not text:
        await actions.send(content="请在 `转码` 后输入需要生成二维码的内容，如网址或文本~")
        return True

    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(API_URL, params={"text": text}) as resp:
                data = await resp.json()
                if str(data.get('code')) == '200' and 'data' in data:
                    await actions.send_file(data['data'])
                else:
                    await actions.send(content="二维码生成失败，请稍后再试~")
    except Exception as e:
        await actions.send(content=f"请求出错：{e}")

    return True
