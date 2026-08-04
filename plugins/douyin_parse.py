"""抖音视频解析插件

触发方式（群聊）：
    抖音 <v.douyin.com短链 / douyin.com视频链接 / iesdouyin分享链接 / 纯视频ID>

流程：还原短链 → 提取 aweme_id → 请求 iesdouyin 分享页（SSR 数据）→ 输出描述/作者/数据统计 + 封面图。
"""

import json
import re
import time

TRIGGHT_KEYWORD = "抖音 "
HELP_MESSAGE = "抖音 <分享链接或视频ID> -> 解析视频信息与封面"

UA = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.douyin.com/",
}

# 各类链接形态：
#   https://v.douyin.com/xxxx/           短链（需还原）
#   https://www.douyin.com/video/{id}
#   https://www.iesdouyin.com/share/video/{id}/
#   https://www.douyin.com/?modal_id={id}
#   纯数字 ID
PATTERNS = [
    r"v\.douyin\.com/[A-Za-z0-9]+",
    r"(?:www\.|m\.)?(?:douyin|iesdouyin)\.com/(?:share/)?video/(\d+)",
    r"modal_id=(\d+)",
    r"\b\d{15,20}\b",
]

ROUTER_RE = re.compile(r"window\._ROUTER_DATA\s*=\s*(\{.*?\})\s*</script>", re.S)


def _parse_duration(ms) -> str:
    """抖音 item.video.duration 单位为毫秒。"""
    try:
        secs = int(ms or 0) // 1000
    except (TypeError, ValueError):
        return "未知"
    if secs <= 0:
        return "未知"
    m, s = secs // 60, secs % 60
    if m >= 60:
        h, m = m // 60, m % 60
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


def _extract_aweme_id(order: str) -> str | None:
    """从消息中提取 aweme_id（纯数字串）或待还原的短链 URL。"""
    order = order.strip()
    for pattern in PATTERNS:
        m = re.search(pattern, order)
        if not m:
            continue
        # 短链返回原始串，其余返回捕获的数字
        if "v.douyin.com" in pattern:
            return m.group(0)
        if m.lastindex:
            return m.group(1)
        return m.group(0)
    return None


async def _resolve_short_link(session, url: str) -> str:
    """还原 v.douyin.com 短链为最终播放页 URL（httpx 需 follow_redirects=True）。"""
    resp = await session.get(url, headers=UA, follow_redirects=True, timeout=10)
    return str(resp.url)


def _final_id_from_url(url: str) -> str | None:
    """从还原后的 URL 提取 aweme_id。"""
    m = re.search(r"/video/(\d+)", url)
    if m:
        return m.group(1)
    m = re.search(r"modal_id=(\d+)", url)
    if m:
        return m.group(1)
    return None


def _pick_url(url_list) -> str:
    """优先挑选 https 直链。"""
    for u in url_list or []:
        if isinstance(u, str) and u.startswith("https://"):
            return u
    return (url_list or [''])[0]


async def on_message(event, actions, **kwargs):
    order = kwargs.get("order", "") or ""
    raw = _extract_aweme_id(order)
    if not raw:
        await actions.send(content=f"无法识别抖音链接，用法：{HELP_MESSAGE}")
        return True

    import httpx

    try:
        async with httpx.AsyncClient() as session:
            aweme_id = raw
            if raw.startswith("v.douyin.com") or "v.douyin.com/" in raw:
                url = "https://" + raw if not raw.startswith("http") else raw
                final = await _resolve_short_link(session, url)
                aweme_id = _final_id_from_url(final) or _extract_aweme_id(final)
            if not aweme_id or not re.fullmatch(r"\d{15,20}", aweme_id):
                await actions.send(content="未能识别出有效的抖音视频ID，链接可能已失效。")
                return True

            share_url = (
                f"https://www.iesdouyin.com/share/video/{aweme_id}/"
                f"?region=CN&mid={aweme_id}&u_code=0&did=0&iid=0&with_sec_did=0"
            )
            resp = await session.get(share_url, headers=UA, timeout=12)
            html = resp.text
    except Exception as e:
        await actions.send(content=f"解析请求失败: {e}")
        return True

    m = ROUTER_RE.search(html)
    if not m:
        await actions.send(content="页面数据解析失败，可能抖音风控拦截，请稍后再试。")
        return True
    try:
        data = json.loads(m.group(1))
        page = data.get("loaderData", {}).get("video_(id)/page") or {}
        vres = page.get("videoInfoRes") or {}
        item_list = vres.get("item_list") or []
    except (json.JSONDecodeError, AttributeError):
        await actions.send(content="页面数据格式异常，解析失败。")
        return True

    if not item_list:
        filters = vres.get("filter_list") or []
        reason = filters[0].get("filter_reason", "") if filters else ""
        hint = "视频不存在或已被删除"
        if "NOT_EXIST" in reason:
            hint = "视频不存在或已被删除"
        elif reason:
            hint = f"视频不可见（{reason}）"
        await actions.send(content=f"解析失败：{hint}")
        return True

    item = item_list[0]
    author = item.get("author") or {}
    video = item.get("video") or {}
    stats = item.get("statistics") or {}
    cover = video.get("cover") or {}

    desc = (item.get("desc") or "").strip() or "（无描述）"
    nickname = author.get("nickname") or "未知"
    duration = _parse_duration(video.get("duration"))
    digg = _format_num(stats.get("digg_count"))
    comment = _format_num(stats.get("comment_count"))
    share = _format_num(stats.get("share_count"))
    collect = _format_num(stats.get("collect_count"))

    ts = item.get("create_time")
    pub = ""
    if ts:
        pub = time.strftime("%Y-%m-%d", time.localtime(ts))

    cover_url = _pick_url(cover.get("url_list"))
    if cover_url.startswith("http://"):
        cover_url = "https://" + cover_url[7:]

    lines = [
        f"【抖音视频】{desc}",
        f"作者：{nickname}",
        f"时长：{duration}",
        f"点赞：{digg}｜评论：{comment}｜收藏：{collect}｜转发：{share}",
    ]
    if pub:
        lines.append(f"发布时间：{pub}")

    await actions.send(content="\n".join(lines))

    if cover_url:
        await actions.send_file(url=cover_url)
    return True
