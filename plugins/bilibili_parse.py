"""B 站视频解析插件

触发方式（群聊）：
    b站 <b23.tv短链 / bilibili.com链接 / BV号 / av号>

功能：还原短链 → 调用官方 view API → 输出视频信息卡片图（Pillow 合成）。
"""

import logging
import math
import re
import time
from io import BytesIO

import httpx
from PIL import Image, ImageDraw, ImageFont

_logger = logging.getLogger("bilibili_parse")

TRIGGER_KEYWORD = "Any"
HELP_MESSAGE = "b站 <b23.tv短链或BV号> -> 解析视频信息与封面"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com/",
}
API_VIEW = "https://api.bilibili.com/x/web-interface/view"
PATTERNS = [
    r"(?:https?://)?(?:www\.)?b23\.tv/[A-Za-z0-9]+",
    r"(?:https?://)?(?:www\.|m\.)?bilibili\.com/video/(BV[0-9A-Za-z]+|av\d+)",
    r"\bBV[0-9A-Za-z]{10}\b",
    r"\bav\d+\b",
]

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
ACCENT_COIN = (255, 213, 79)
ICON_SIZE = 14


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
    order = order.strip()
    for pattern in PATTERNS:
        m = re.search(pattern, order, re.IGNORECASE)
        if m:
            return m.group(0)
    return None


def _extract_bvid(url_or_id: str) -> str | None:
    m = re.search(r"BV[0-9A-Za-z]{10}", url_or_id, re.IGNORECASE)
    if m:
        return m.group(0)
    m = re.search(r"av(\d+)", url_or_id, re.IGNORECASE)
    if m:
        return m.group(0)
    return None


async def _resolve_short_link(session, url: str) -> str:
    resp = await session.get(url, headers=HEADERS, follow_redirects=True, timeout=10)
    return str(resp.url)


async def _download_image(session, url: str) -> bytes | None:
    if not url:
        return None
    try:
        resp = await session.get(url, headers=HEADERS, timeout=15)
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
    title: str,
    owner_name: str,
    owner_face_bytes: bytes | None,
    pub_str: str,
    duration: str,
    view: str,
    danmaku: str,
    reply: str,
    like: str,
    favorite: str,
    coin: str,
    share: str,
    cover_bytes: bytes | None,
) -> BytesIO:
    """用 Pillow 合成 B 站视频信息卡片，返回 PNG BytesIO。"""
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

    # 卡片背景
    card_rect = [PAD, PAD, CARD_W - PAD, CARD_H - PAD]
    draw.rounded_rectangle(card_rect, radius=16, fill=CARD_BG, outline=BORDER_COLOR, width=1)

    # ---- 标题 ----
    title_x = PAD + 16
    title_y = PAD + 16
    max_title_w = CARD_W - PAD * 2 - 32
    title_lines = _wrap_text(title, font_title, max_title_w)
    for i, line in enumerate(title_lines):
        draw.text((title_x, title_y + i * 26), line, fill=TITLE_COLOR, font=font_title)

    # 分割线
    div_y = title_y + len(title_lines) * 26 + 10
    draw.line([(title_x, div_y), (CARD_W - PAD - 16, div_y)], fill=BORDER_COLOR, width=1)

    # ---- 左侧信息 ----
    info_x = PAD + 16
    info_y = div_y + 15
    row_gap = 24

    # 行1: 头像 + UP主名
    avatar_size = 34
    if owner_face_bytes:
        try:
            avatar = Image.open(BytesIO(owner_face_bytes)).convert("RGBA")
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
    draw.text((name_x, info_y + 8), owner_name, fill=VALUE_COLOR, font=font_label)

    # 行2: 发布时间 + 时长
    row2_y = info_y + row_gap + 8
    time_text = f"发布时间: {pub_str}  |  时长: {duration}" if pub_str else f"时长: {duration}"
    draw.text((info_x, row2_y), time_text, fill=LABEL_COLOR, font=font_small)

    # 行3: 播放 + 评论
    row3_y = row2_y + row_gap
    _draw_stat_row(
        draw, info_x, row3_y,
        "play", "播放", view, ACCENT_PLAY,
        "comment", "评论", reply, ACCENT_CMT,
        font_label, font_value,
    )

    # 行4: 点赞 + 收藏
    row4_y = row3_y + row_gap
    _draw_stat_row(
        draw, info_x, row4_y,
        "like", "点赞", like, ACCENT_LIKE,
        "star", "收藏", favorite, ACCENT_FAV,
        font_label, font_value,
    )

    # 行5: 分享 + 投币
    row5_y = row4_y + row_gap
    _draw_stat_row(
        draw, info_x, row5_y,
        "share", "分享", share, ACCENT_SHARE,
        "coin", "投币", coin, ACCENT_COIN,
        font_label, font_value,
    )

    # 弹幕
    danmaku_y = row5_y + row_gap
    _draw_icon(draw, info_x, danmaku_y + 1, "danmaku", ACCENT_CMT, ICON_SIZE)
    draw.text((info_x + ICON_SIZE + 4, danmaku_y), f"弹幕: {danmaku}", fill=LABEL_COLOR, font=font_small)

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


async def on_message(ctx):
    event = ctx.event
    actions = ctx.actions
    kwargs = ctx.kwargs
    order = kwargs.get("order", "") or ""
    target = _extract_target(order)
    if not target:
        # 仅当用户主动发起命令时才回复帮助，其余消息静默略过
        if order.lower().startswith("b站"):
            await actions.send(content=f"无法识别链接，用法：{HELP_MESSAGE}")
            return True
        return False

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
    owner = d.get("owner") or {}
    owner_name = owner.get("name", "未知")
    owner_face = owner.get("face", "")
    duration = _parse_duration(d.get("duration", 0))
    stat = d.get("stat") or {}
    view = _format_num(stat.get("view"))
    like = _format_num(stat.get("like"))
    danmaku = _format_num(stat.get("danmaku"))
    reply = _format_num(stat.get("reply"))
    favorite = _format_num(stat.get("favorite"))
    coin = _format_num(stat.get("coin"))
    share = _format_num(stat.get("share"))
    pic = d.get("pic", "")
    if pic.startswith("http://"):
        pic = "https://" + pic[7:]
    bvid_final = d.get("bvid") or bvid
    pubdate = d.get("pubdate")
    pub_str = ""
    if pubdate:
        pub_str = time.strftime("%Y-%m-%d", time.localtime(pubdate))

    # 下载封面图和头像
    try:
        async with httpx.AsyncClient() as session:
            cover_bytes = await _download_image(session, pic) if pic else None
            avatar_bytes = await _download_image(session, owner_face) if owner_face else None
    except Exception:
        _logger.exception("下载封面/头像时出错")
        cover_bytes = None
        avatar_bytes = None

    # 生成卡片图
    try:
        card_buf = _generate_card(
            title=title,
            owner_name=owner_name,
            owner_face_bytes=avatar_bytes,
            pub_str=pub_str,
            duration=duration,
            view=view,
            danmaku=danmaku,
            reply=reply,
            like=like,
            favorite=favorite,
            coin=coin,
            share=share,
            cover_bytes=cover_bytes,
        )
        _logger.info("卡片图片大小: %d bytes", card_buf.getbuffer().nbytes)
        await actions.send_file(file=card_buf, filename="bilibili_card.jpg")
    except Exception:
        _logger.exception("生成/发送卡片失败")
    return True
