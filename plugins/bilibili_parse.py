"""B 站视频解析插件

触发方式（群聊）：
    b站 <b23.tv短链 / bilibili.com链接 / BV号 / av号>

功能：还原短链 → 调用官方 view API → 输出标题/UP/时长/数据统计，并发送封面图。
"""

import re

TRIGGHT_KEYWORD = "b站 "
HELP_MESSAGE = "b站 <b23.tv短链或BV号> -> 解析视频信息与封面"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}
API_VIEW = "https://api.bilibili.com/x/web-interface/view"
PATTERNS = [
    r"(?:https?://)?(?:www\.)?b23\.tv/[A-Za-z0-9]+",
    r"(?:https?://)?(?:www\.|m\.)?bilibili\.com/video/(BV[0-9A-Za-z]+|av\d+)",
    r"\bBV[0-9A-Za-z]{10}\b",
    r"\bav\d+\b",
]


def _parse_duration(seconds: int) -> str:
    seconds = int(seconds or 0)
    h, m, s = seconds // 3600, (seconds % 3600) // 60, seconds % 60
    if h:
        return f"{h}小时{m}分{s}秒"
    if m:
        return f"{m}分{s}秒"
    return f"{s}秒"


def _format_num(num) -> str:
    try:
        num = int(num or 0)
    except (TypeError, ValueError):
        return "0"
    if num >= 100_000_000:
        return f"{num / 100_000_000:.2f}亿"
    if num >= 10_000:
        return f"{num / 10_000:.1f}万"
    return str(num)


def _extract_target(order: str) -> str | None:
    """从消息中提取目标链接/BV号/av号，按优先级返回。"""
    order = order.strip()
    # 优先完整匹配 URL
    for pattern in PATTERNS:
        m = re.search(pattern, order, re.IGNORECASE)
        if m:
            return m.group(0)
    return None


def _extract_bvid(url_or_id: str) -> str | None:
    """从链接/BV号/av号中提取标准 bvid。

    注意：B站 BV 号大小写敏感（大小写不同的 BV 串是不同视频），
    必须保留原始大小写，不能做 upper/lower 归一化。
    """
    m = re.search(r"BV[0-9A-Za-z]{10}", url_or_id, re.IGNORECASE)
    if m:
        return m.group(0)
    m = re.search(r"av(\d+)", url_or_id, re.IGNORECASE)
    if m:
        return m.group(0)  # av123 形式 view API 同样支持
    return None


async def _resolve_short_link(session, url: str) -> str:
    """还原 b23.tv 短链为完整播放页 URL（httpx 默认不自动跟随重定向）。"""
    resp = await session.get(url, headers=HEADERS, follow_redirects=True, timeout=10)
    return str(resp.url)


async def on_message(event, actions, **kwargs):
    order = kwargs.get("order", "") or ""
    target = _extract_target(order)
    if not target:
        await actions.send(content=f"无法识别链接，用法：{HELP_MESSAGE}")
        return True

    import httpx

    try:
        async with httpx.AsyncClient() as session:
            url = target
            if "b23.tv" in target:
                url = await _resolve_short_link(session, target)
                bvid = _extract_bvid(url)
                if not bvid:
                    await actions.send(content="短链还原后未能识别出视频编号，可能链接已失效。")
                    return True
            else:
                bvid = _extract_bvid(target)

            if not bvid:
                await actions.send(content=f"未能从链接中识别出视频编号，用法：{HELP_MESSAGE}")
                return True

            resp = await session.get(API_VIEW, params={"bvid": bvid}, headers=HEADERS, timeout=10)
            data = resp.json()
    except Exception as e:
        await actions.send(content=f"解析请求失败: {e}")
        return True

    if data.get("code") != 0 or not data.get("data"):
        msg = data.get("message") or data.get("msg") or "视频不存在或已删除"
        await actions.send(content=f"解析失败：{msg}")
        return True

    d = data["data"]
    title = d.get("title", "")
    owner = (d.get("owner") or {}).get("name", "未知")
    duration = _parse_duration(d.get("duration", 0))
    stat = d.get("stat") or {}
    view = _format_num(stat.get("view"))
    like = _format_num(stat.get("like"))
    danmaku = _format_num(stat.get("danmaku"))
    bvid = d.get("bvid") or bvid
    pic = d.get("pic", "")
    if pic.startswith("http://"):
        pic = "https://" + pic[7:]
    pubdate = d.get("pubdate")
    pub_str = ""
    if pubdate:
        import time

        pub_str = time.strftime("%Y-%m-%d", time.localtime(pubdate))

    text = (
        f"【B站视频】{title}\n"
        f"UP主：{owner}\n"
        f"时长：{duration}\n"
        f"播放：{view}｜点赞：{like}｜弹幕：{danmaku}\n"
        f"发布时间：{pub_str}\n"
        f"链接：https://www.bilibili.com/video/{bvid}"
    )
    await actions.send(content=text)
    if pic:
        await actions.send_file(url=pic)
    return True
