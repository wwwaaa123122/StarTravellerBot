# -*- coding: utf-8 -*-
"""权限判定：黑名单 / 管理员（ROOT_User）。

配置位置：black_list 在 config.json 顶层，ROOT_User 在 Others 段。
"""

from typing import Any


def is_blacklisted(user_id: str, config: dict) -> bool:
    """用户是否在黑名单中（黑名单用户的消息被静默忽略）。"""
    blacklist = config.get("black_list", []) or []
    return user_id in blacklist


def is_root(user_id: str, config: dict) -> bool:
    """用户是否为管理员（ROOT_User）。"""
    root_users = config.get("Others", {}).get("ROOT_User", []) or []
    return user_id in root_users
