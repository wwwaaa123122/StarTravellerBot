# -*- coding: utf-8 -*-
"""Ping 插件 - 适配 QQ 开放平台"""

import asyncio
import json
import socket
import re
import logging
_logger = logging.getLogger("ping")
import logging

TRIGGHT_KEYWORD = "ping "
HELP_MESSAGE = "ping <域名或IP> -> 对目标执行ping并返回IP信息"


async def _run_ping(host: str) -> str:
    """执行 ping 命令"""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", "4", "-W", "2", host,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        return out.decode(errors="ignore")
    except Exception as e:
        return f"[ping 执行失败] {e!r}"


def _extract_latencies_ms(ping_text: str):
    """提取延迟值"""
    times = []
    for m in re.finditer(r"time[=<]?\s*=?\s*([\d\.]+)\s*ms", ping_text):
        try:
            times.append(float(m.group(1)))
        except Exception:
            pass
    return times[:4]


def _resolve_ip(host: str) -> str:
    """解析 IP"""
    try:
        socket.inet_pton(socket.AF_INET, host)
        return host
    except OSError:
        pass
    try:
        socket.inet_pton(socket.AF_INET6, host)
        return host
    except OSError:
        pass
    info = socket.getaddrinfo(host, None)
    if not info:
        raise RuntimeError("DNS 解析失败")
    return info[0][4][0]


async def _fetch_geo(ip: str) -> dict:
    """获取 IP 地理位置"""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(f"http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,isp,as,query")
            data = response.json()
            if data.get("status") != "success":
                return {"error": data.get("message", "查询失败")}
            return data
    except Exception as e:
        return {"error": str(e)}


async def on_message(event, actions, **kwargs):
    """处理 ping 命令"""
    content = event.message if hasattr(event, 'message') else ""
    
    # 提取目标
    if content.startswith("ping "):
        target = content[5:].strip()
    else:
        target = content.strip()
    
    if not target:
        await actions.send(content="用法: ping <域名或IP>\n例如: ping 1.1.1.1")
        return True
    
    try:
        ip = await asyncio.get_running_loop().run_in_executor(None, _resolve_ip, target)
    except Exception as e:
        await actions.send(content=f"目标: {target}\nDNS 解析失败: {e}")
        return True
    
    # 并行执行 ping 和地理位置查询
    ping_task = asyncio.create_task(_run_ping(ip))
    geo_task = asyncio.create_task(_fetch_geo(ip))
    ping_text, geo = await asyncio.gather(ping_task, geo_task)
    
    times = _extract_latencies_ms(ping_text)
    
    if times:
        avg = sum(times) / len(times)
        times_line = "、".join(f"{t:.1f}ms" for t in times)
    else:
        avg = None
        times_line = "未解析到延迟值"
    
    # 地理位置信息
    if "error" in geo:
        geo_text = f"地理位置: {geo['error']}"
    else:
        parts = []
        loc = " / ".join(filter(None, [geo.get("country"), geo.get("regionName"), geo.get("city")]))
        if loc:
            parts.append(f"位置: {loc}")
        if geo.get("isp"):
            parts.append(f"ISP: {geo['isp']}")
        geo_text = "\n".join(parts) if parts else "地理位置: 未知"
    
    # 格式化地理位置文本（如果有多行则用缩进）
    if "错误" in geo_text or "未知" in geo_text:
        geo_formatted = f"- {geo_text}"
    else:
        geo_formatted = geo_text
    
    lines = [
        "## 🌐 Ping 结果",
        "",
        f"- **目标**: {target}",
        f"- **解析IP**: {ip}",
        geo_formatted,
        f"- **延迟**: {times_line}",
        f"- **平均延迟**: {avg:.1f}ms" if avg else "- **平均延迟**: 未知",
    ]
    
    await actions.send(content="\n".join(lines))
    return True
