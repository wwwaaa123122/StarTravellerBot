# -*- coding: utf-8 -*-
"""HTTP状态检测插件 - 适配 QQ 开放平台"""

import asyncio
import time
from urllib.parse import urlparse

TRIGGHT_KEYWORD = "http"
HELP_MESSAGE = "http <网址> -> 检查网址的HTTP状态码"


async def on_message(event, actions, **kwargs):
    """处理HTTP状态检测"""
    content = event.message if hasattr(event, 'message') else ""

    # 提取网址
    if content.startswith("http"):
        url = content[4:].strip()
    else:
        url = content.strip()

    if not url:
        await actions.send(content="用法: http <网址>\n例如: http https://example.com\nhttp google.com")
        return True

    # 确保URL有协议前缀
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    # 验证URL格式
    try:
        parsed_url = urlparse(url)
        if not parsed_url.netloc:  # 如果没有域名部分
            raise ValueError("无效的URL")
    except Exception:
        await actions.send(content="提供的网址格式无效，请检查后重试")
        return True

    # 发送等待消息
    await actions.send(content=f"🔍 正在检测 {url} …")

    try:
        start_time = time.time()

        # 使用 curl -I -L -s 发送 HEAD 请求并跟随重定向
        proc = await asyncio.create_subprocess_exec(
            'curl', '-I', '-L', '-s', url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            elapsed = time.time() - start_time
            error_msg = f"❌ 请求超时 ({elapsed:.2f}s)"
            await actions.send(content=error_msg)
            return True

        elapsed = time.time() - start_time

        # 模拟加载延迟，确保不会瞬间闪回结果
        if elapsed < 1.5:
            await asyncio.sleep(1.5 - elapsed)

        stdout_text = stdout.decode('utf-8', errors='replace').strip()
        stderr_text = stderr.decode('utf-8', errors='replace').strip()

        # 显示原始 curl 输出（仅保留关键行：状态行 + 常用响应头）
        if stdout_text:
            lines = stdout_text.split('\n')
            keep_headers = {'http/', 'content-type', 'content-length', 'location',
                          'server', 'date', 'set-cookie', 'x-', 'cache-control', 'cf-'}
            filtered = []
            for line in lines:
                low_line = line.lower().strip()
                # 状态行和关键头保留
                if low_line.startswith('http/') or \
                   any(low_line.startswith(h) for h in keep_headers):
                    filtered.append(line.strip())
            result = '\n'.join(filtered)
        else:
            result = f"curl 无输出 (返回码: {proc.returncode})"

        # 拼装结果
        result_message = f"## HTTP 检测结果\n\n`$ curl -I {url}`\n\n```\n{result}\n```\n\n- **⏱ 耗时**: {elapsed:.2f}s"
        if stderr_text:
            result_message += f"\n- **stderr**: `{stderr_text[:200]}`"

        await actions.send(content=result_message)

    except Exception as e:
        error_msg = f"发生未知错误：{str(e)}"
        await actions.send(content=error_msg)

    return True
