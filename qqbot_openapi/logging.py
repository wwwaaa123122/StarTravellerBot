# -*- coding: utf-8 -*-

import logging as _logging

__all__ = ("get_logger",)

_DEFAULT_NAME = "qqbot_openapi"


def get_logger(name: str | None = None) -> _logging.Logger:
    return _logging.getLogger(name or _DEFAULT_NAME)
