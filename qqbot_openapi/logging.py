# -*- coding: utf-8 -*-
"""日志工具

与旧版 botpy.logging 保持兼容：``get_logger(name=None)`` 返回一个标准库
``logging.Logger``，默认命名空间为包名。
"""

import logging as _logging

__all__ = ("get_logger",)

_DEFAULT_NAME = "qqbot_openapi"


def get_logger(name: str | None = None) -> _logging.Logger:
    """获取日志器

    Args:
        name: 日志器名称，None 时使用默认命名空间
    """
    return _logging.getLogger(name or _DEFAULT_NAME)
