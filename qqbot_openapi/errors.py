# -*- coding: utf-8 -*-


class QQBotError(Exception):
    pass


class AccessTokenError(QQBotError):
    pass


class APIError(QQBotError):

    def __init__(self, code: int, message: str, request_id: str = ""):
        self.code = code
        self.message = message
        self.request_id = request_id
        super().__init__(f"API error: code={code}, message={message}, request_id={request_id}")


class GatewayError(QQBotError):
    pass


class WebSocketClosedError(GatewayError):

    def __init__(self, code: int, reason: str = ""):
        self.code = code
        self.reason = reason
        super().__init__(f"WebSocket closed with code {code}: {reason}")


class NotSupportError(QQBotError):
    pass
