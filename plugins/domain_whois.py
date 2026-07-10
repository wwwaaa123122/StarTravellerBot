# -*- coding: utf-8 -*-
"""域名Whois查询插件 - 适配 QQ 开放平台"""

import asyncio
import re
import socket
from datetime import datetime
from typing import Dict, List, Optional, Any

TRIGGHT_KEYWORD = "whois"
HELP_MESSAGE = "whois <域名> -> 查询域名注册信息（含中文翻译）"

import logging

_logger = logging.getLogger("Whois")

# 尝试导入 whois 模块
try:
    import whois as whois_module
    WHOIS_AVAILABLE = True
except ImportError:
    WHOIS_AVAILABLE = False
    _logger.warning("python-whois 未安装")


def _extract_contact_info(w) -> Dict[str, Any]:
    """提取联系人和邮箱信息"""
    contact_info: Dict[str, Any] = {}

    # 注册人信息
    if hasattr(w, 'registrant_name') and w.registrant_name:
        contact_info['registrant'] = w.registrant_name
    elif hasattr(w, 'name') and w.name:
        contact_info['registrant'] = w.name

    # 注册组织
    if hasattr(w, 'registrant_organization') and w.registrant_organization:
        contact_info['organization'] = w.registrant_organization
    elif hasattr(w, 'org') and w.org:
        contact_info['organization'] = w.org

    # 邮箱信息 - 尝试多个可能的字段
    emails = set()

    email_fields = ['emails', 'registrant_email', 'admin_email', 'tech_email',
                    'email', 'registrar_email', 'billing_email']

    for field in email_fields:
        if hasattr(w, field) and getattr(w, field):
            email_value = getattr(w, field)
            if isinstance(email_value, list):
                for email in email_value:
                    if email and isinstance(email, str) and '@' in email:
                        emails.add(email.strip().lower())
            elif isinstance(email_value, str) and '@' in email_value:
                emails.add(email_value.strip().lower())

    # 从原始文本中提取邮箱（备用方法）
    if not emails and hasattr(w, 'text'):
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        found_emails = re.findall(email_pattern, w.text)
        emails.update([email.lower() for email in found_emails])

    contact_info['emails'] = list(emails)

    # 地址信息
    if hasattr(w, 'registrant_address') and w.registrant_address:
        contact_info['address'] = w.registrant_address
    elif hasattr(w, 'address') and w.address:
        contact_info['address'] = w.address

    # 国家信息
    if hasattr(w, 'registrant_country') and w.registrant_country:
        contact_info['country'] = w.registrant_country
    elif hasattr(w, 'country') and w.country:
        contact_info['country'] = w.country

    return contact_info


def _format_whois_info(domain: str) -> str:
    """获取并格式化 whois 信息"""
    if not WHOIS_AVAILABLE:
        return "❌ Whois 模块未安装，请在服务器上执行: pip install python-whois"
    
    try:
        w = whois_module.whois(domain)

        # 格式化结果
        info = [f"## 🌐 Whois 查询结果 for {domain}"]

        # 基础域名信息
        info.append("\n### 📄 基础信息")
        if w.domain_name:
            domain_name = w.domain_name
            if isinstance(domain_name, list):
                domain_name = domain_name[0]
            info.append(f"- **域名 (Domain)**: {domain_name}")

        if w.registrar:
            info.append(f"- **注册商 (Registrar)**: {w.registrar}")

        # 时间信息
        if w.creation_date:
            creation = w.creation_date
            if isinstance(creation, list):
                creation = creation[0]
            if isinstance(creation, datetime):
                creation = creation.strftime("%Y-%m-%d %H:%M:%S")
            info.append(f"- **创建时间 (Creation Date)**: {creation}")

        if w.updated_date:
            update = w.updated_date
            if isinstance(update, list):
                update = update[0]
            if isinstance(update, datetime):
                update = update.strftime("%Y-%m-%d %H:%M:%S")
            info.append(f"- **更新时间 (Updated Date)**: {update}")

        if w.expiration_date:
            expiry = w.expiration_date
            if isinstance(expiry, list):
                expiry = expiry[0]
            if isinstance(expiry, datetime):
                expiry = expiry.strftime("%Y-%m-%d %H:%M:%S")
            info.append(f"- **过期时间 (Expiry Date)**: {expiry}")

        # 联系人和邮箱信息
        contact_info = _extract_contact_info(w)

        info.append("\n### 👤 注册人信息")
        if contact_info.get('registrant'):
            info.append(f"- **注册人 (Registrant)**: {contact_info['registrant']}")
        else:
            info.append("- **注册人 (Registrant)**: [信息被隐藏]")

        if contact_info.get('organization'):
            info.append(f"- **组织 (Organization)**: {contact_info['organization']}")

        if contact_info.get('emails'):
            emails = contact_info['emails']
            if len(emails) == 1:
                info.append(f"- **邮箱 (Email)**: {emails[0]}")
            else:
                info.append("- **邮箱 (Emails)**:")
                for email in emails[:3]:  # 最多显示3个邮箱
                    info.append(f"  - {email}")
                if len(emails) > 3:
                    info.append(f"  - ... 还有 {len(emails) - 3} 个邮箱")
        else:
            info.append("- **邮箱 (Email)**: [信息被隐藏]")

        if contact_info.get('country'):
            info.append(f"- **国家 (Country)**: {contact_info['country']}")

        # 技术信息
        info.append("\n### 🔧 技术信息")
        if w.name_servers:
            ns = w.name_servers
            if isinstance(ns, list):
                ns = ", ".join(ns[:6])  # 最多显示5个NS
                if len(w.name_servers) > 5:
                    ns += f" ... (共{len(w.name_servers)}个)"
            info.append(f"- **域名服务器 (Name Servers)**: {ns}")

        if w.status:
            status = w.status
            if isinstance(status, list):
                status = ", ".join(status)
            info.append(f"- **状态 (Status)**: {status}")

        # 注册商信息
        if hasattr(w, 'registrar_url') and w.registrar_url:
            info.append(f"- **注册商网址 (Registrar URL)**: {w.registrar_url}")

        if hasattr(w, 'registrar_abuse_contact_email') and w.registrar_abuse_contact_email:
            info.append(f"- **注册商滥用投诉邮箱**: {w.registrar_abuse_contact_email}")

        info.append("\n> **💡 提示**: 部分域名信息可能被隐私保护服务隐藏")

        return "\n".join(info) if info else "未能获取到有效的 Whois 信息。"

    except Exception as e:
        return f"Whois 查询失败: {str(e)}\n请检查域名格式是否正确，或稍后重试。"


async def on_message(event, actions, **kwargs):
    """处理 whois 查询"""
    content = event.message if hasattr(event, 'message') else ""

    # 提取域名
    if content.startswith("whois"):
        domain = content[5:].strip()
    else:
        domain = content.strip()

    if not domain:
        await actions.send(content="用法: whois <域名>\n例如: whois example.com\nwhois google.com")
        return True

    # 简单的域名格式验证
    if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$', domain):
        await actions.send(content="域名格式不正确，请检查后重试")
        return True

    # 发送查询中提示
    await actions.send(content=f"🔍 正在查询域名 {domain} 的WHOIS信息...")
    
    # 添加延迟避免消息去重
    await asyncio.sleep(1)

    # 执行查询
    try:
        _logger.info(f"正在查询: {domain}")
        result = await asyncio.get_running_loop().run_in_executor(None, _format_whois_info, domain)
        _logger.info(f"查询完成，结果长度: {len(result)}")

        # 限制输出长度，避免刷屏
        if len(result) > 1500:
            result = result[:1500] + "\n...结果过长已截断，建议使用专业WHOIS工具查看完整信息..."

        await actions.send(content=result)
    except Exception as e:
        _logger.error(f"查询失败: {e}")
        await actions.send(content="❌ 查询失败，请稍后重试")
    
    return True
