"""
AI Function Calling 模块
- 定义所有可用工具的 OpenAI schema
- 权限控制（ROOT 用户可操作所有工具，普通用户仅安全工具）
- 工具执行器（mock event/actions，捕获插件输出）
"""

import json
import logging
from typing import Any, Callable

logger = logging.getLogger("function_calling")

# ---------------------------------------------------------------------------
# 工具定义（OpenAI Function Calling 格式）
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "weather",
            "description": "查询指定城市的天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，例如：北京、上海、东京",
                    }
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ping",
            "description": "对指定目标执行 ping 检测，返回延迟和连通性信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "目标地址，可以是域名或 IP，例如：example.com 或 1.1.1.1",
                    }
                },
                "required": ["target"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hitokoto",
            "description": "获取随机一言（励志、动画、漫画等类型的短句）",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "checkin",
            "description": "用户每日签到，获取签到奖励和连续签到天数",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "whois",
            "description": "查询域名的 WHOIS 信息，包括注册商、到期时间等",
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "要查询的域名，例如：example.com",
                    }
                },
                "required": ["domain"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mc_status",
            "description": "查询 Minecraft 服务器状态，包括在线玩家数、延迟等",
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "Minecraft 服务器地址，可带端口，例如：mc.example.com 或 1.2.3.4:25565",
                    }
                },
                "required": ["address"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "acg_picture",
            "description": "生成一张二次元图片（ACG）",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "图片类型：随机、电脑壁纸、手机壁纸、头像、背景",
                        "enum": ["随机", "电脑壁纸", "手机壁纸", "头像", "背景"],
                    }
                },
                "required": ["type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "qr_code",
            "description": "将文字或 URL 生成为二维码图片",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "要编码为二维码的文本或 URL",
                    }
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "affection",
            "description": "查询用户对机器人的好感度",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kick_query",
            "description": "查询指定主播的直播开播状态",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "主播名称",
                    }
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kick_list",
            "description": "列出所有正在监控的主播",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kick_check",
            "description": "检查所有监控主播的开播状态",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kick_status",
            "description": "查看 kick 监控系统的运行状态",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kick_add",
            "description": "添加一个新的主播到监控列表（仅管理员可用）",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "要添加监控的主播名称",
                    }
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kick_del",
            "description": "从监控列表中删除一个主播（仅管理员可用）",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "要删除的主播名称",
                    }
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kick_interval",
            "description": "设置监控检查间隔（秒，最低 30 秒）（仅管理员可用）",
            "parameters": {
                "type": "object",
                "properties": {
                    "seconds": {
                        "type": "integer",
                        "description": "检查间隔秒数，最少 30 秒",
                    }
                },
                "required": ["seconds"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kick_start",
            "description": "启动 kick 监控系统（仅管理员可用）",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kick_stop",
            "description": "停止 kick 监控系统（仅管理员可用）",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# 权限定义
# ---------------------------------------------------------------------------

# 所有工具及其权限级别
# "anyone": 所有用户可用
# "root": 仅 ROOT 用户可用
TOOL_PERMISSIONS = {
    "weather": "anyone",
    "ping": "anyone",
    "hitokoto": "anyone",
    "checkin": "anyone",
    "whois": "anyone",
    "mc_status": "anyone",
    "acg_picture": "anyone",
    "qr_code": "anyone",
    "affection": "anyone",
    "kick_query": "anyone",
    "kick_list": "anyone",
    "kick_check": "anyone",
    "kick_status": "anyone",
    "kick_add": "root",
    "kick_del": "root",
    "kick_interval": "root",
    "kick_start": "root",
    "kick_stop": "root",
}


def get_available_tools(user_id: str, root_users: set) -> list:
    """根据用户权限返回可用的工具定义列表"""
    is_root = user_id in root_users
    available = []
    for tool in TOOL_DEFINITIONS:
        name = tool["function"]["name"]
        permission = TOOL_PERMISSIONS.get(name, "root")
        if permission == "anyone" or is_root:
            available.append(tool)
    return available


# ---------------------------------------------------------------------------
# 工具处理器注册表
# ---------------------------------------------------------------------------

# 格式: tool_name -> (plugin_module, message_builder)
# message_builder: Callable[[dict], str] - 接收工具参数 dict，返回命令字符串
_TOOL_HANDLERS: dict[str, tuple[Any, Callable[[dict], str]]] = {}


def _register_tool(tool_name: str, plugin_module: Any, message_builder: Callable[[dict], str]):
    """注册工具处理器"""
    _TOOL_HANDLERS[tool_name] = (plugin_module, message_builder)


def _load_plugin(module_name: str):
    """延迟加载插件模块"""
    import importlib
    return importlib.import_module(module_name)


def _init_handlers():
    """初始化所有工具处理器（延迟加载插件模块）"""
    if _TOOL_HANDLERS:
        return

    _register_tool("weather", _load_plugin("plugins.weather"),
                   lambda args: f"天气 {args.get('city', '')}")
    _register_tool("ping", _load_plugin("plugins.ping"),
                   lambda args: f"ping {args.get('target', '')}")
    _register_tool("hitokoto", _load_plugin("plugins.hitokoto"),
                   lambda args: "一言")
    _register_tool("checkin", _load_plugin("plugins.checkin"),
                   lambda args: "签到")
    _register_tool("whois", _load_plugin("plugins.domain_whois"),
                   lambda args: f"whois {args.get('domain', '')}")
    _register_tool("mc_status", _load_plugin("plugins.mc_status"),
                   lambda args: f"mc状态 {args.get('address', '')}")
    _register_tool("acg_picture", _load_plugin("plugins.acg_picture"),
                   lambda args: f"生图 ACG {args.get('type', '随机')}")
    _register_tool("qr_code", _load_plugin("plugins.qr_code"),
                   lambda args: f"转码 {args.get('text', '')}")
    _register_tool("affection", _load_plugin("plugins.affection"),
                   lambda args: "好感度")

    # Kick 子命令
    kick_module = _load_plugin("plugins.kick")
    _register_tool("kick_query", kick_module,
                   lambda args: f"kick {args.get('name', '')}")
    _register_tool("kick_list", kick_module,
                   lambda args: "kick list")
    _register_tool("kick_check", kick_module,
                   lambda args: "kick check")
    _register_tool("kick_status", kick_module,
                   lambda args: "kick status")
    _register_tool("kick_add", kick_module,
                   lambda args: f"kick add {args.get('name', '')}")
    _register_tool("kick_del", kick_module,
                   lambda args: f"kick del {args.get('name', '')}")
    _register_tool("kick_interval", kick_module,
                   lambda args: f"kick interval {args.get('seconds', 60)}")
    _register_tool("kick_start", kick_module,
                   lambda args: "kick start")
    _register_tool("kick_stop", kick_module,
                   lambda args: "kick stop")


# ---------------------------------------------------------------------------
# Mock Actions - 捕获插件输出
# ---------------------------------------------------------------------------

class _ToolActions:
    """模拟 PluginActions，捕获所有 send() 调用的输出"""

    def __init__(self):
        self._responses: list[str] = []

    async def send(self, **kwargs):
        """捕获文本/图片输出"""
        # 优先处理 markdown
        markdown = kwargs.get('markdown')
        if markdown:
            self._responses.append(str(markdown))
            return

        msg = kwargs.get('content') or kwargs.get('message')
        if msg is not None:
            self._responses.append(self._extract_text(msg))

    async def send_file(self, url: str = None, file_type: int = 1,
                        file=None, filename: str = None):
        """捕获文件发送"""
        if filename:
            self._responses.append(f"[图片已发送: {filename}]")
        elif url:
            self._responses.append(f"[图片已发送: {url}]")
        else:
            self._responses.append("[图片已发送]")

    async def send_local_file(self, file_path: str, file_type: int = 1):
        """捕获本地文件发送"""
        import os
        self._responses.append(f"[文件已发送: {os.path.basename(file_path)}]")

    def _extract_text(self, msg) -> str:
        if isinstance(msg, str):
            return msg
        if hasattr(msg, '__iter__'):
            parts = []
            for part in msg:
                if hasattr(part, 'text'):
                    parts.append(part.text)
                elif isinstance(part, str):
                    parts.append(part)
            return ''.join(parts)
        return str(msg) if msg else ''

    def get_response(self) -> str:
        """获取所有捕获的响应文本"""
        return '\n'.join(self._responses) if self._responses else '(无输出)'


# ---------------------------------------------------------------------------
# 工具执行器
# ---------------------------------------------------------------------------

MAX_TOOL_ITERATIONS = 5  # 最大工具调用轮次，防止死循环


async def execute_tool(
    tool_name: str,
    arguments: dict,
    user_id: str,
    root_users: set,
    config: Any,
    client: Any,
) -> str:
    """执行一个工具调用，返回捕获的插件输出文本"""
    _init_handlers()

    if tool_name not in _TOOL_HANDLERS:
        return f"错误：未知工具 '{tool_name}'"

    # 权限检查
    permission = TOOL_PERMISSIONS.get(tool_name, "root")
    if permission == "root" and user_id not in root_users:
        return "权限不足：此操作需要管理员权限"

    module, msg_builder = _TOOL_HANDLERS[tool_name]
    msg = msg_builder(arguments)

    # 创建 mock event
    event = type('ToolEvent', (), {
        'message': msg,
        'user_id': user_id,
        'nickname': '',
        'group_id': None,
        'message_id': None,
        'self_id': None,
    })()

    # 创建 mock actions
    actions = _ToolActions()

    # 构建 kwargs（兼容所有插件的参数需求，event/actions 作为位置参数传递）
    kwargs = {
        'order': msg,
        'ROOT_User': root_users,
        'config': config,
        'client': client,
        'reminder': '#',
        'bot_name': getattr(config, 'bot_name', '星辰旅人') if hasattr(config, 'bot_name') else '星辰旅人',
    }

    try:
        result = await module.on_message(event, actions, **kwargs)
        # 如果插件返回 False，表示未匹配到命令
        if result is False:
            return f"命令格式错误：{msg}，请检查参数是否正确"
    except Exception as e:
        logger.error(f"执行工具 {tool_name}({arguments}) 出错: {e}", exc_info=True)
        return f"执行工具时出错: {e}"

    return actions.get_response()


# ---------------------------------------------------------------------------
# 系统提示词增强
# ---------------------------------------------------------------------------

FUNCTION_CALLING_SYSTEM_PROMPT = """
你是一个功能丰富的 QQ 机器人助手。你可以使用以下工具来帮助用户：

- 天气查询：用户询问天气相关问题时，调用 weather 工具
- 网络检测：用户要求 ping 服务器时，调用 ping 工具
- 一言：用户想要一句名言或短句时，调用 hitokoto 工具
- 签到：用户说"签到"时，调用 checkin 工具
- WHOIS 查询：用户查询域名信息时，调用 whois 工具
- MC 服务器状态：用户查询 Minecraft 服务器状态时，调用 mc_status 工具
- ACG 图片生成：用户想要二次元图片时，调用 acg_picture 工具
- 二维码生成：用户要求生成二维码时，调用 qr_code 工具
- 好感度查询：用户询问对自己的好感度时，调用 affection 工具
- Kick 直播监控：用户查询主播开播状态时，调用 kick_query
- Kick 监控列表：用户要求列出监控主播时，调用 kick_list
- Kick 状态检查：用户要求检查所有主播状态时，调用 kick_check
- Kick 系统状态：用户询问监控系统运行状态时，调用 kick_status

使用工具时请注意：
1. 优先使用工具获取实时信息，而不是凭记忆回答
2. 工具返回的结果请自然地融入对话中
3. 如果工具返回错误，请向用户解释并提供替代方案
4. 对于不需要工具就能回答的问题（如聊天、常识），直接回答即可
"""