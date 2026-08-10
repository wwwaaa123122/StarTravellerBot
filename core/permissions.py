# -*- coding: utf-8 -*-

from typing import Any

def is_blacklisted(user_id: str, config: dict) -> bool:
    blacklist = config.get("black_list", []) or []
    return user_id in blacklist


def is_root(user_id: str, config: dict) -> bool:
    root_users = config.get("Others", {}).get("ROOT_User", []) or []
    return user_id in root_users
