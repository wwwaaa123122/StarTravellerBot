"""抖音视频解析插件

触发方式（群聊）：
    抖音 <v.douyin.com短链 / douyin.com视频链接 / iesdouyin分享链接 / 纯视频ID>

流程：还原短链 → 提取 aweme_id → 请求 iesdouyin 分享页（SSR 数据）→ 输出视频信息卡片图（Pillow 合成）。
"""

import json
import logging
import math
import re
import time
from io import BytesIO

import httpx
from PIL import Image, ImageDraw, ImageFont

_logger = logging.getLogger("douyin_parse")

TRIGGER_KEYWORD = "Any"
HELP_MESSAGE = "抖音 <分享链接或视频ID> -> 解析视频信息与封面"

UA = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.douyin.com/",
}

PATTERNS = [
    r"v\.douyin\.com/[A-Za-z0-9]+",
    r"(?:www\.|m\.)?(?:douyin|iesdouyin)\.com/(?:share/)?video/(\d+)",
    r"modal_id=(\d+)",
    r"\b\d{15,20}\b",
]

ROUTER_RE = re.compile(r"window\._ROUTER_DATA\s*=\s*(\{.*?\})\s*</script>", re.S)

# ---- 字体 & 常量 ----
FONT_PATH = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
CARD_W, CARD_H = 720, 405
PAD = 24
LEFT_W = 322
COVER_X = PAD + LEFT_W + 16
COVER_MAX_W = CARD_W - COVER_X - PAD

BG_COLOR = (15, 15, 26)
CARD_BG = (26, 26, 46)
BORDER_COLOR = (42, 42, 74)
TITLE_COLOR = (255, 255, 255)
LABEL_COLOR = (139, 139, 158)
VALUE_COLOR = (224, 224, 255)
ACCENT_PLAY = (79, 195, 247)
ACCENT_LIKE = (239, 83, 80)
ACCENT_CMT = (102, 187, 106)
ACCENT_FAV = (255, 167, 38)
ACCENT_SHARE = (171, 71, 188)
ICON_SIZE = 14


def _parse_duration(ms) -> str:
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
    order = order.strip()
    for pattern in PATTERNS:
        m = re.search(pattern, order)
        if not m:
            continue
        if "v.douyin.com" in pattern:
            return m.group(0)
        if m.lastindex:
            return m.group(1)
        return m.group(0)
    return None


async def _resolve_short_link(session, url: str) -> str:
    resp = await session.get(url, headers=UA, follow_redirects=True, timeout=10)
    return str(resp.url)


def _final_id_from_url(url: str) -> str | None:
    m = re.search(r"/video/(\d+)", url)
    if m:
        return m.group(1)
    m = re.search(r"modal_id=(\d+)", url)
    if m:
        return m.group(1)
    return None


def _pick_url(url_list) -> str:
    for u in url_list or []:
        if isinstance(u, str) and u.startswith("https://"):
            return u
    return (url_list or [""])[0]


async def _download_image(session, url: str) -> bytes | None:
    if not url:
        return None
    try:
        resp = await session.get(url, headers=UA, timeout=15)
        if resp.status_code == 200:
            return resp.content
        else:
            _logger.warning("图片下载失败: %s, HTTP %s", url, resp.status_code)
    except Exception as e:
        _logger.warning("图片下载出错: %s, %s", url, e)
    return None


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines = []
    current = ""
    for char in text:
        test = current + char
        if font.getlength(test) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines[:2]


def _make_circle_mask(size: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    return mask


def _draw_icon(draw, x, y, icon_type, color, size):
    """Draw a simple geometric icon using Pillow drawing primitives."""
    s = size

    if icon_type == "play":
        draw.polygon([(x, y), (x + s, y + s // 2), (x, y + s)], fill=color)
    elif icon_type == "comment":
        draw.rounded_rectangle([x, y, x + s, y + s - 4], radius=3, fill=color)
        draw.polygon([(x + 3, y + s - 4), (x + 6, y + s), (x + 9, y + s - 4)], fill=color)
    elif icon_type == "like":
        r = s // 4
        draw.ellipse([x, y, x + 2 * r, y + 2 * r], fill=color)
        draw.ellipse([x + s - 2 * r, y, x + s, y + 2 * r], fill=color)
        draw.polygon([(x, y + r), (x + s, y + r), (x + s // 2, y + s)], fill=color)
    elif icon_type == "star":
        cx, cy = x + s // 2, y + s // 2
        outer_r = s // 2
        inner_r = s // 4
        points = []
        for i in range(10):
            angle = -math.pi / 2 + i * math.pi / 5
            r = outer_r if i % 2 == 0 else inner_r
            points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        draw.polygon(points, fill=color)
    elif icon_type == "share":
        draw.arc([x, y, x + s, y + s], 0, 180, fill=color, width=2)
        draw.polygon([(x, y + s // 2 + 1), (x + 4, y + s // 2 - 3), (x + 4, y + s // 2 + 5)], fill=color)
        draw.polygon([(x + s, y + s // 2 - 1), (x + s - 4, y + s // 2 + 3), (x + s - 4, y + s // 2 - 5)], fill=color)
    elif icon_type == "coin":
        draw.ellipse([x + 1, y + 1, x + s - 1, y + s - 1], fill=color)
    elif icon_type == "danmaku":
        draw.rounded_rectangle([x, y, x + s, y + s - 4], radius=2, fill=color)
        draw.polygon([(x + 2, y + s - 4), (x + 5, y + s), (x + 8, y + s - 4)], fill=color)


def _draw_stat_row(draw, x, y, icon1, label1, val1, color1, icon2, label2, val2, color2, font_l, font_v):
    icon_size = ICON_SIZE
    gap = 4
    half_w = 150
    icon_y = y + 1

    _draw_icon(draw, x, icon_y, icon1, color1, icon_size)
    tx = x + icon_size + gap
    draw.text((tx, y), label1, fill=LABEL_COLOR, font=font_l)
    lw = font_l.getlength(label1)
    draw.text((tx + lw + 6, y), val1, fill=color1, font=font_v)

    x2 = x + half_w
    _draw_icon(draw, x2, icon_y, icon2, color2, icon_size)
    tx2 = x2 + icon_size + gap
    draw.text((tx2, y), label2, fill=LABEL_COLOR, font=font_l)
    lw2 = font_l.getlength(label2)
    draw.text((tx2 + lw2 + 6, y), val2, fill=color2, font=font_v)


def _generate_card(
    desc: str,
    nickname: str,
    avatar_bytes: bytes | None,
    pub_str: str,
    duration: str,
    play_count: str,
    comment_count: str,
    digg_count: str,
    collect_count: str,
    share_count: str,
    cover_bytes: bytes | None,
    aweme_id: str,
) -> BytesIO:
    """用 Pillow 合成抖音视频信息卡片，返回 PNG BytesIO。"""
    img = Image.new("RGB", (CARD_W, CARD_H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype(FONT_PATH, 20)
        font_label = ImageFont.truetype(FONT_PATH, 14)
        font_value = ImageFont.truetype(FONT_PATH, 14)
        font_small = ImageFont.truetype(FONT_PATH, 12)
    except Exception:
        font_title = ImageFont.load_default()
        font_label = font_title
        font_value = font_title
        font_small = font_title

    card_rect = [PAD, PAD, CARD_W - PAD, CARD_H - PAD]
    draw.rounded_rectangle(card_rect, radius=16, fill=CARD_BG, outline=BORDER_COLOR, width=1)

    # ---- 标题（视频描述） ----
    title_x = PAD + 16
    title_y = PAD + 16
    max_title_w = CARD_W - PAD * 2 - 32
    title_lines = _wrap_text(desc, font_title, max_title_w)
    for i, line in enumerate(title_lines):
        draw.text((title_x, title_y + i * 26), line, fill=TITLE_COLOR, font=font_title)

    div_y = title_y + len(title_lines) * 26 + 10
    draw.line([(title_x, div_y), (CARD_W - PAD - 16, div_y)], fill=BORDER_COLOR, width=1)

    # ---- 左侧信息 ----
    info_x = PAD + 16
    info_y = div_y + 15
    row_gap = 24

    # 行1: 头像 + 作者名
    avatar_size = 34
    if avatar_bytes:
        try:
            avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA")
            avatar = avatar.resize((avatar_size, avatar_size), Image.LANCZOS)
            mask = _make_circle_mask(avatar_size)
            img.paste(avatar, (info_x, info_y), mask)
        except Exception:
            draw.ellipse(
                [info_x, info_y, info_x + avatar_size, info_y + avatar_size],
                fill=(60, 60, 80),
            )
    else:
        draw.ellipse(
            [info_x, info_y, info_x + avatar_size, info_y + avatar_size],
            fill=(60, 60, 80),
        )

    name_x = info_x + avatar_size + 12
    draw.text((name_x, info_y + 8), nickname, fill=VALUE_COLOR, font=font_label)

    # 行2: 发布时间 + 时长
    row2_y = info_y + row_gap + 8
    time_text = f"发布时间: {pub_str}  |  时长: {duration}" if pub_str else f"时长: {duration}"
    draw.text((info_x, row2_y), time_text, fill=LABEL_COLOR, font=font_small)

    # 行3: 播放 + 评论
    row3_y = row2_y + row_gap
    _draw_stat_row(
        draw, info_x, row3_y,
        "play", "播放", play_count, ACCENT_PLAY,
        "comment", "评论", comment_count, ACCENT_CMT,
        font_label, font_value,
    )

    # 行4: 点赞 + 收藏
    row4_y = row3_y + row_gap
    _draw_stat_row(
        draw, info_x, row4_y,
        "like", "点赞", digg_count, ACCENT_LIKE,
        "star", "收藏", collect_count, ACCENT_FAV,
        font_label, font_value,
    )

    # 行5: 分享
    row5_y = row4_y + row_gap
    _draw_icon(draw, info_x, row5_y + 1, "share", ACCENT_SHARE, ICON_SIZE)
    draw.text((info_x + ICON_SIZE + 4, row5_y), "分享", fill=LABEL_COLOR, font=font_label)
    lw = font_label.getlength("分享")
    draw.text((info_x + ICON_SIZE + 4 + lw + 6, row5_y), share_count, fill=ACCENT_SHARE, font=font_value)

    # 视频链接
    link_y = row5_y + row_gap
    draw.text(
        (info_x, link_y),
        f"链接: https://www.douyin.com/video/{aweme_id}",
        fill=LABEL_COLOR,
        font=font_small,
    )

    # ---- 右侧封面 ----
    if cover_bytes:
        try:
            cover = Image.open(BytesIO(cover_bytes)).convert("RGB")
            cw, ch = cover.size
            target_w = COVER_MAX_W
            target_h = int(ch * target_w / cw)
            max_cover_h = CARD_H - PAD - info_y - 10
            if target_h > max_cover_h:
                target_h = max_cover_h
                target_w = int(cw * target_h / ch)
            cover = cover.resize((target_w, target_h), Image.LANCZOS)

            cover_mask = Image.new("L", (target_w, target_h), 0)
            mask_draw = ImageDraw.Draw(cover_mask)
            mask_draw.rounded_rectangle([0, 0, target_w, target_h], radius=12, fill=255)

            cover_x_offset = COVER_X + (COVER_MAX_W - target_w) // 2
            img.paste(cover, (cover_x_offset, info_y), cover_mask)
        except Exception:
            pass

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    buf.seek(0)
    return buf


async def on_message(event, actions, **kwargs):
    order = kwargs.get("order", "") or ""
    raw = _extract_aweme_id(order)
    if not raw:
        # 仅当用户主动发起命令时才回复帮助，其余消息静默略过
        if order.startswith("抖音"):
            await actions.send(content=f"无法识别抖音链接，用法：{HELP_MESSAGE}")
            return True
        return False

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
    play_count = _format_num(stats.get("play_count"))
    comment_count = _format_num(stats.get("comment_count"))
    digg_count = _format_num(stats.get("digg_count"))
    collect_count = _format_num(stats.get("collect_count"))
    share_count = _format_num(stats.get("share_count"))

    # 作者头像
    avatar_thumb = author.get("avatar_thumb") or {}
    avatar_url = _pick_url(avatar_thumb.get("url_list"))
    if not avatar_url:
        avatar_medium = author.get("avatar_medium") or {}
        avatar_url = _pick_url(avatar_medium.get("url_list"))

    ts = item.get("create_time")
    pub_str = ""
    if ts:
        pub_str = time.strftime("%Y-%m-%d", time.localtime(ts))

    cover_url = _pick_url(cover.get("url_list"))
    if cover_url.startswith("http://"):
        cover_url = "https://" + cover_url[7:]

    # 下载封面和头像
    try:
        async with httpx.AsyncClient() as session:
            cover_bytes = await _download_image(session, cover_url) if cover_url else None
            avatar_bytes = await _download_image(session, avatar_url) if avatar_url else None
    except Exception:
        _logger.exception("下载封面/头像时出错")
        cover_bytes = None
        avatar_bytes = None

    # 生成卡片图
    try:
        card_buf = _generate_card(
            desc=desc,
            nickname=nickname,
            avatar_bytes=avatar_bytes,
            pub_str=pub_str,
            duration=duration,
            play_count=play_count,
            comment_count=comment_count,
            digg_count=digg_count,
            collect_count=collect_count,
            share_count=share_count,
            cover_bytes=cover_bytes,
            aweme_id=aweme_id,
        )
        _logger.info("卡片图片大小: %d bytes", card_buf.getbuffer().nbytes)
        await actions.send_file(file=card_buf, filename="douyin_card.jpg")
    except Exception:
        _logger.exception("生成/发送卡片失败")
    return True