# -*- coding: utf-8 -*-
"""qqbot_openapi 异常定义"""


class QQBotError(Exception):
    """QQ 开放平台 SDK 基础异常"""


class AccessTokenError(QQBotError):
    """获取访问凭证（getAppAccessToken）失败"""


class APIError(QQBotError):
    """调用开放平台 API 时返回业务错误

    属性:
        code: 错误码（0 表示成功）
        message: 错误描述
        request_id: 请求唯一标识
    """

    def __init__(self, code: int, message: str, request_id: str = ""):
        self.code = code
        self.message = message
        self.request_id = request_id
        super().__init__(f"API error: code={code}, message={message}, request_id={request_id}")


class GatewayError(QQBotError):
    """WebSocket 网关连接错误"""


class WebSocketClosedError(GatewayError):
    """网关 WebSocket 连接被关闭

    属性:
        code: 关闭码（4001-4915 为鉴权/频控错误，见官方文档）
    """

    def __init__(self, code: int, reason: str = ""):
        self.code = code
        self.reason = reason
        super().__init__(f"WebSocket closed with code {code}: {reason}")


class NotSupportError(QQBotError):
    """接口或参数不被支持"""
