# -*- coding: utf-8 -*-

import asyncio
import time
from urllib.parse import urlparse

TRIGGER_KEYWORD = "http"
HELP_MESSAGE = "http <网址> -> 检查网址的HTTP状态码"


async def on_message(ctx):
    event = ctx.event
    actions = ctx.actions
    kwargs = ctx.kwargs
    content = event.message if hasattr(event, 'message') else ""

    if content.startswith("http"):
        url = content[4:].strip()
    else:
        url = content.strip()

    if not url:
        await actions.send(content="用法: http <网址>\n例如: http https://example.com\nhttp google.com")
        return True

    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    try:
        parsed_url = urlparse(url)
        if not parsed_url.netloc:
            raise ValueError("无效的URL")
    except Exception:
        await actions.send(content="提供的网址格式无效，请检查后重试")
        return True

    await actions.send(content=f"🔍 正在检测 {url} …")

    try:
        start_time = time.time()

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

        if elapsed < 1.5:
            await asyncio.sleep(1.5 - elapsed)

        stdout_text = stdout.decode('utf-8', errors='replace').strip()
        stderr_text = stderr.decode('utf-8', errors='replace').strip()

        if stdout_text:
            lines = stdout_text.split('\n')
            keep_headers = {'http/', 'content-type', 'content-length', 'location',
                          'server', 'date', 'set-cookie', 'x-', 'cache-control', 'cf-'}
            filtered = []
            for line in lines:
                low_line = line.lower().strip()
                if low_line.startswith('http/') or \
                   any(low_line.startswith(h) for h in keep_headers):
                    filtered.append(line.strip())
            result = '\n'.join(filtered)
        else:
            result = f"curl 无输出 (返回码: {proc.returncode})"

        result_message = f"## HTTP 检测结果\n\n`$ curl -I {url}`\n\n```\n{result}\n```\n\n- **⏱ 耗时**: {elapsed:.2f}s"
        if stderr_text:
            result_message += f"\n- **stderr**: `{stderr_text[:200]}`"

        await actions.send(content=result_message)

    except Exception as e:
        error_msg = f"发生未知错误：{str(e)}"
        await actions.send(content=error_msg)

    return True
