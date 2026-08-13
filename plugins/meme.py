# -*- coding: utf-8 -*-
"""基于 meme-generator 的表情包生成插件。

用法（群聊 @机器人 触发）：
    @机器人 表情 <表情名> [@用户 / 附带图片] [文本...]
    @机器人 表情 悲报 我币呢？
    @机器人 表情 摸 @朋友
    @机器人 表情 列表 [页码]
    @机器人 表情 搜索 <关键词>
    @机器人 表情 帮助 [表情名]

同时也支持 meme-generator 自带的关键字直接触发，如：@机器人 摸 @朋友
"""

import asyncio
import io
import logging
import os
import re
import sys
import time

_logger = logging.getLogger("meme")

TRIGGER_KEYWORDS = ["表情", "meme", "Any"]
HELP_MESSAGE = "表情/meme <meme名> [@用户] [文本] -> 生成沙雕表情包（发送 @机器人 /meme 帮助 查看用法）"

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ASSETS_DIR = os.path.join(_PROJECT_ROOT, "assets")
_ASSETS_MEME_DIR = os.path.join(_ASSETS_DIR, "meme")
_BG_H_PATH = os.path.join(_ASSETS_DIR, "bg-h.jpg")
_HELP_IMG_PATH = os.path.join(_ASSETS_DIR, "meme_help.png")
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
]

_WRAPPERS = ("表情", "meme")
_MENTION_RE = re.compile(r"<@!?([A-Za-z0-9_-]+)>")
_COOLDOWN_SECONDS = 10
_LIST_PAGE_SIZE = 50

_cooldowns: dict = {}

_memes = None
_keyword_map = None
_resources_ready = False
_resources_checking = False
_help_image_path = None


def _ensure_loaded():
    """懒加载 meme_generator 并构建关键字索引（首次调用触发）。"""
    global _memes, _keyword_map
    if _memes is None:
        import meme_generator  # noqa: F401  # 导入即注册全部内置表情
        from meme_generator import get_memes

        _memes = get_memes()
        _keyword_map = {}
        for meme in _memes:
            for kw in meme.keywords:
                _keyword_map.setdefault(kw, []).append(meme)
        _logger.info(f"meme 插件已加载 {len(_memes)} 个表情")
    return _memes, _keyword_map


def _find_meme(name: str):
    _, _keyword_map = _ensure_loaded()
    name = name.strip()
    if name in _keyword_map:
        return _keyword_map[name][0]
    for meme in _memes:
        if meme.key == name:
            return meme
    return None


def _resources_present() -> bool:
    """探测资源是否已下载（避免每次全量 hash 校验）。"""
    try:
        from pathlib import Path

        from meme_generator import __file__ as _meme_file

        probe = Path(_meme_file).parent / "memes" / "bad_news" / "images" / "0.png"
        return probe.exists()
    except Exception:
        return False


def _run_check_resources():
    """静默执行资源检查/下载（首次使用时会拉取图片与字体资源）。"""
    from meme_generator.download import check_resources

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()  # 屏蔽 rich 进度条输出
    try:
        asyncio.run(check_resources())
    finally:
        sys.stdout = old_stdout


def _provision_from_assets() -> bool:
    """将 assets/meme 内的本地资源供给到已安装的 meme_generator 包目录。"""
    if not os.path.isdir(_ASSETS_MEME_DIR):
        return False
    try:
        from shutil import copy2

        from meme_generator import __file__ as _meme_file

        dst_root = os.path.join(os.path.dirname(_meme_file), "memes")
        copied = 0
        for root, _dirs, files in os.walk(_ASSETS_MEME_DIR):
            for name in files:
                src = os.path.join(root, name)
                rel = os.path.relpath(src, _ASSETS_MEME_DIR)
                dst = os.path.join(dst_root, rel)
                if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src):
                    continue
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                copy2(src, dst)
                copied += 1
        _logger.info(f"meme 本地资源供给完成，共复制 {copied} 个文件")
        return True
    except Exception as e:
        _logger.error(f"meme 本地资源供给失败: {e}")
        return False


async def _ensure_resources() -> bool:
    global _resources_ready, _resources_checking
    if _resources_ready:
        return True
    try:
        from meme_generator.download import check_resources  # noqa: F401
    except ImportError:
        return False

    if _resources_checking:
        while _resources_checking:
            await asyncio.sleep(1)
        return _resources_ready

    _resources_checking = True
    try:
        # 优先使用项目内 assets/meme 本地资源，避免运行时联网下载
        if _provision_from_assets():
            _resources_ready = True
            return True
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _run_check_resources)
        _resources_ready = True
        return True
    except Exception as e:
        _logger.error(f"meme 资源准备失败: {e}")
        return False
    finally:
        _resources_checking = False


def _parse_cmd(cmd: str):
    """从命令中提取 @openid 列表和剩余文本。"""
    mentions = _MENTION_RE.findall(cmd)
    rest = _MENTION_RE.sub("", cmd).strip()
    texts = [t for t in rest.split() if t]
    return mentions, texts


def _get_mentions(ctx, cmd: str) -> list:
    """合并命令与原始消息中的 @ 提及，排除机器人自身。

    全量群消息（SCENE_GROUP）中提及会被 dispatcher 从 order 剥离，
    但原始 message.content 仍保留 <@!openid>，从这里补回即可拿到被 @ 用户。
    """
    mentions = _MENTION_RE.findall(cmd)
    raw = getattr(getattr(ctx, "message", None), "content", "") or ""
    if raw:
        mentions += _MENTION_RE.findall(raw)

    bot_ids = set()
    appid = _get_appid(ctx)
    if appid:
        bot_ids.add(appid)
    try:
        rid = getattr(ctx.client.robot, "id", None)
        if rid:
            bot_ids.add(str(rid))
    except Exception:
        pass

    seen = []
    for m in mentions:
        if m in bot_ids or m in seen:
            continue
        seen.append(m)
    return seen


def _get_attachment_urls(ctx) -> list:
    message = getattr(ctx, "message", None)
    if message is None:
        return []
    attachments = getattr(message, "attachments", None) or []
    urls = []
    for att in attachments:
        if isinstance(att, dict):
            url = att.get("url")
        else:
            url = getattr(att, "url", None)
        if url:
            urls.append(url)
    return urls


async def _download_bytes(ctx, url: str):
    try:
        resp = await ctx.client.http_client.get(url)
        if resp.status_code == 200 and resp.content:
            return resp.content
    except Exception as e:
        _logger.debug(f"下载图片失败 {url}: {e}")
    return None


def _get_appid(ctx) -> str:
    """获取机器人 appid（config > SDK client）。"""
    try:
        cfg = getattr(ctx, "config", None) or {}
        appid = (cfg.get("OpenQQ") or {}).get("appid", "")
        if appid:
            return str(appid)
    except Exception:
        pass
    try:
        appid = getattr(ctx.client, "_appid", None)
        if appid:
            return str(appid)
    except Exception:
        pass
    return ""


async def _fetch_avatar(ctx, openid: str):
    """通过 q.qlogo.cn 官方头像服务直接拼接链接获取头像，无需白名单权限。"""
    if not openid:
        return None
    appid = _get_appid(ctx)
    if not appid:
        _logger.debug("获取头像失败：缺少 appid")
        return None
    url = f"https://q.qlogo.cn/qqapp/{appid}/{openid}/0"
    return await _download_bytes(ctx, url)


async def _collect_images(ctx, meme, mentions: list) -> list:
    """收集表情所需图片：消息附件 -> @用户头像 -> 发送者头像兜底。"""
    max_images = meme.params_type.max_images
    if max_images == 0:
        return []

    images: list = []
    attachments = _get_attachment_urls(ctx)
    for url in attachments[: max_images]:
        data = await _download_bytes(ctx, url)
        if data:
            images.append(data)
            if len(images) >= max_images:
                return images

    for openid in mentions:
        data = await _fetch_avatar(ctx, openid)
        if data:
            images.append(data)
            if len(images) >= max_images:
                return images

    if len(images) < meme.params_type.min_images:
        data = await _fetch_avatar(ctx, getattr(ctx, "user_id", ""))
        if data:
            images.append(data)
    return images


def _generate_sync(meme, images, texts):
    return meme(images=images, texts=texts)


async def _generate(ctx, meme, cmd: str, user_id: str = ""):
    actions = ctx.actions

    now = time.time()
    if user_id in _cooldowns and now - _cooldowns[user_id] < _COOLDOWN_SECONDS:
        remaining = _COOLDOWN_SECONDS - (now - _cooldowns[user_id])
        await actions.send(content=f"⏳ 表情生成冷却中，请等待 **{remaining:.1f}** 秒")
        return True
    _cooldowns[user_id] = now

    mentions = _get_mentions(ctx, cmd)
    _, texts = _parse_cmd(cmd)

    if not _resources_ready and not _resources_present():
        await actions.send(content="⏳ 首次使用需要下载表情资源，请稍候...")

    ok = await _ensure_resources()
    if not ok:
        await actions.send(content="❌ 表情资源准备失败，请检查网络后重试")
        return True

    images = await _collect_images(ctx, meme, mentions)
    if not texts and meme.params_type.default_texts:
        texts = list(meme.params_type.default_texts)

    try:
        result = await asyncio.get_running_loop().run_in_executor(
            None, _generate_sync, meme, images, texts
        )
    except Exception as e:
        _logger.error(f"生成表情 {meme.key} 失败: {e!r}")
        from meme_generator.exception import MemeGeneratorException

        if isinstance(e, MemeGeneratorException):
            await actions.send(content=f"❌ {e}")
        else:
            await actions.send(content=f"❌ 生成表情「{meme.key}」失败，请检查参数是否正确")
        return True

    if result is None:
        await actions.send(content="❌ 生成结果为空，请稍后再试")
        return True

    result.seek(0)
    await actions.send_file(file=result, filename=f"{meme.key}.png")
    return True


def _find_font() -> str:
    """查找可渲染中文的字体文件。"""
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return ""


def _generate_help_image() -> bool:
    """用 bg-h.jpg 生成表情列表帮助图（卡片模糊风格），保存到 assets/meme_help.png。"""
    try:
        from PIL import Image, ImageDraw, ImageFilter, ImageFont

        memes, _ = _ensure_loaded()
        if not memes or not os.path.exists(_BG_H_PATH):
            return False

        font_path = _find_font()
        if not font_path:
            return False

        bg = Image.open(_BG_H_PATH).convert("RGB")
        bg_w, bg_h = bg.size

        # 条目：每个 meme 的主关键字名
        entries = []
        for meme in sorted(memes, key=lambda m: m.key):
            name = meme.keywords[0] if meme.keywords else meme.key
            entries.append(name)

        # 布局参数
        cols = 4
        rows = (len(entries) + cols - 1) // cols
        line_h = 40
        header_h = 300
        card_pad_x = 70
        col_gap = 30
        row_pad = 20
        content_h = rows * line_h
        canvas_h = header_h + row_pad + content_h + 80

        # 背景：纵向平铺 bg 后整体模糊，形成无缝渐变
        canvas = Image.new("RGB", (bg_w, canvas_h))
        y = 0
        while y < canvas_h:
            canvas.paste(bg, (0, y))
            y += bg_h
        canvas = canvas.filter(ImageFilter.GaussianBlur(radius=32))
        canvas = canvas.convert("RGBA")
        dark = Image.new("RGBA", canvas.size, (0, 0, 0, 120))
        canvas = Image.alpha_composite(canvas, dark).convert("RGB")

        draw = ImageDraw.Draw(canvas, "RGBA")

        def _font(size: int):
            return ImageFont.truetype(font_path, size)

        # 头部卡片
        draw.rounded_rectangle(
            (card_pad_x, 46, bg_w - card_pad_x, header_h - 40),
            radius=30,
            fill=(255, 255, 255, 64),
            outline=(255, 255, 255, 150),
            width=2,
        )
        draw.text(
            (bg_w / 2, 118), "表情包生成",
            font=_font(64), fill=(255, 255, 255, 255), anchor="mm",
        )
        draw.text(
            (bg_w / 2, 196), "示例：@机器人 /meme 摸摸",
            font=_font(34), fill=(255, 224, 90, 255), anchor="mm",
        )
        draw.text(
            (bg_w / 2, 252),
            f"共 {len(memes)} 个表情 · @用户或附带图片可作为头像素材",
            font=_font(24), fill=(255, 255, 255, 230), anchor="mm",
        )

        # 内容卡片
        content_top = header_h + row_pad
        draw.rounded_rectangle(
            (card_pad_x, content_top - 18, bg_w - card_pad_x, canvas_h - 36),
            radius=30,
            fill=(255, 255, 255, 52),
            outline=(255, 255, 255, 120),
            width=2,
        )

        name_font = _font(26)
        col_w = (bg_w - 2 * card_pad_x - (cols - 1) * col_gap) // cols
        for i, name in enumerate(entries):
            r, c = divmod(i, cols)
            x = card_pad_x + c * (col_w + col_gap)
            y = content_top + r * line_h
            draw.text(
                (x, y), f"{i + 1:>3}. {name}",
                font=name_font, fill=(255, 255, 255, 255), anchor="lm",
            )

        canvas.save(_HELP_IMG_PATH, format="PNG")
        _logger.info(f"meme 帮助图已生成: {_HELP_IMG_PATH} ({canvas.size})")
        return True
    except Exception as e:
        _logger.error(f"meme 帮助图生成失败: {e}")
        return False


async def _get_help_image() -> str:
    """获取预生成的帮助图路径，不存在则现场生成。"""
    global _help_image_path
    if _help_image_path and os.path.exists(_help_image_path):
        return _help_image_path
    if not os.path.exists(_HELP_IMG_PATH):
        ok = await asyncio.get_running_loop().run_in_executor(None, _generate_help_image)
        if not ok:
            return ""
    _help_image_path = _HELP_IMG_PATH
    return _HELP_IMG_PATH


async def _send_general_help(ctx):
    actions = ctx.actions
    try:
        img_path = await _get_help_image()
        if img_path and os.path.exists(img_path):
            await actions.send_local_file(img_path)
            return True
    except Exception as e:
        _logger.error(f"发送帮助图失败: {e}")

    _, _keyword_map = _ensure_loaded()
    lines = [
        "## 🎨 表情包生成",
        "",
        "**发送格式**：`@机器人 表情 <表情名> [@用户] [文本]`",
        "",
        "**示例**：",
        "- `@机器人 表情 摸 @朋友` （使用对方头像）",
        "- `@机器人 表情 摸 [附带图片]` （使用消息图片）",
        "- `@机器人 表情 悲报 我币呢？` （文本表情）",
        "",
        "**其他命令**：",
        "- `表情 列表 [页码]` 查看全部表情",
        "- `表情 搜索 <关键词>` 搜索表情",
        "- `表情 帮助 <表情名>` 查看单个表情用法",
        "",
        f"已内置 **{len(_memes)}** 个表情，也可直接发送 `@机器人 摸 @朋友` 等关键字触发",
    ]
    await actions.send(content="\n".join(lines))
    return True


async def _send_meme_info(ctx, meme):
    actions = ctx.actions
    p = meme.params_type
    lines = [
        f"## 🎨 {meme.key}",
        f"- **关键字**：{' / '.join(meme.keywords) or '无'}",
        f"- **图片**：{p.min_images} ~ {p.max_images} 张",
        f"- **文本**：{p.min_texts} ~ {p.max_texts} 条",
    ]
    if p.default_texts:
        lines.append(f"- **默认文本**：{' / '.join(p.default_texts)}")
    if meme.tags:
        lines.append(f"- **标签**：{'、'.join(sorted(meme.tags))}")
    lines.append("")
    lines.append(f"💡 用法：`@机器人 表情 {meme.keywords[0] if meme.keywords else meme.key} ...`")
    await actions.send(content="\n".join(lines))
    return True


async def _send_meme_list(ctx, page: int):
    actions = ctx.actions
    _, _keyword_map = _ensure_loaded()
    memes = sorted(_memes, key=lambda m: m.key)
    total_pages = max(1, (len(memes) + _LIST_PAGE_SIZE - 1) // _LIST_PAGE_SIZE)
    page = min(max(page, 1), total_pages)

    start = (page - 1) * _LIST_PAGE_SIZE
    chunk = memes[start:start + _LIST_PAGE_SIZE]
    lines = [
        f"## 🎨 表情列表（{page}/{total_pages} 页，共 {len(memes)} 个）",
        "",
    ]
    for i, meme in enumerate(chunk, start=start + 1):
        kw = meme.keywords[0] if meme.keywords else meme.key
        lines.append(f"{i}. **{kw}**（{meme.key}）")
    lines.append("")
    lines.append("💡 使用 `@机器人 表情 列表 <页码>` 翻页，`表情 搜索 <词>` 查找")
    await actions.send(content="\n".join(lines))
    return True


async def _handle_wrapper(ctx, cmd: str, user_id: str = ""):
    actions = ctx.actions
    try:
        _ensure_loaded()
    except Exception as e:
        _logger.error(f"meme 加载失败: {e}")
        await actions.send(content="❌ 表情功能未就绪（缺少 meme-generator 依赖）")
        return True

    cmd = cmd.strip()
    if not cmd:
        return await _send_general_help(ctx)

    parts = cmd.split(None, 1)
    first, rest = parts[0], (parts[1] if len(parts) > 1 else "")

    if first in ("帮助", "help", "?"):
        if rest:
            meme = _find_meme(rest)
            if meme:
                return await _send_meme_info(ctx, meme)
            await actions.send(content=f"❌ 未找到表情「{rest}」，可用 `表情 搜索 {rest}` 查找")
            return True
        return await _send_general_help(ctx)

    if first in ("列表", "list", "ls"):
        try:
            page = int(rest) if rest.strip().isdigit() else 1
        except ValueError:
            page = 1
        return await _send_meme_list(ctx, page)

    if first in ("搜索", "search", "find"):
        keyword = rest.strip()
        if not keyword:
            await actions.send(content="用法：`表情 搜索 <关键词>`")
            return True
        _, _keyword_map = _ensure_loaded()
        matched = [
            meme for meme in _memes
            if keyword in meme.key
            or any(keyword in kw for kw in meme.keywords)
            or any(keyword in tag for tag in meme.tags)
        ]
        if not matched:
            await actions.send(content=f"🔍 未找到包含「{keyword}」的表情")
            return True
        lines = [f"## 🔍 搜索「{keyword}」，找到 {len(matched)} 个", ""]
        for meme in sorted(matched, key=lambda m: m.key)[:20]:
            kw = '/'.join(meme.keywords) or meme.key
            lines.append(f"- **{kw}**（{meme.key}）")
        if len(matched) > 20:
            lines.append(f"... 等共 {len(matched)} 个")
        lines.append("")
        lines.append("💡 使用 `@机器人 表情 <表情名>` 生成")
        await actions.send(content="\n".join(lines))
        return True

    meme = _find_meme(first)
    if meme is None:
        await actions.send(
            content=f"❌ 未找到表情「{first}」\n\n"
            f"可用 `表情 搜索 {first}` 查找，或 `表情 列表` 查看全部"
        )
        return True

    return await _generate(ctx, meme, rest, user_id)


async def on_message(ctx):
    event = ctx.event
    actions = ctx.actions
    order = (ctx.order or "").strip()
    user_id = str(getattr(event, "user_id", "") or "")

    if not order:
        return False

    # 包装命令：表情/meme <meme> ...（要求空格/结尾，避免误触发如“表情包”）
    for _wrapper in _WRAPPERS:
        if order == _wrapper or order.startswith(_wrapper + " ") or order.startswith(_wrapper + "<@"):
            cmd = order[len(_wrapper):].strip()
            return await _handle_wrapper(ctx, cmd, user_id)

    # 直接关键字触发（最长匹配，要求关键字后有空格/@/结尾，避免误触发）
    try:
        _, _keyword_map = _ensure_loaded()
    except Exception as e:
        _logger.error(f"meme 加载失败: {e}")
        await actions.send(content="❌ 表情功能未就绪（缺少 meme-generator 依赖）")
        return True

    for kw, memes in sorted(_keyword_map.items(), key=lambda item: -len(item[0])):
        if kw and (
            order == kw
            or order.startswith(kw + " ")
            or order.startswith(kw + "<@")
        ):
            meme = memes[0]
            cmd = order[len(kw):].strip()
            return await _generate(ctx, meme, cmd, user_id)

    return False
