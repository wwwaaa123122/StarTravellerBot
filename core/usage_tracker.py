# -*- coding: utf-8 -*-

"""记录使用过 bot 的群 / 用户（data/groups_list.txt、data/users_list.txt）。"""

import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
GROUPS_FILE = os.path.join(DATA_DIR, "groups_list.txt")
USERS_FILE = os.path.join(DATA_DIR, "users_list.txt")

_seen_groups = None
_seen_users = None


def _load_ids(path):
    ids = set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    ids.add(line)
    except OSError:
        pass
    return ids


def _ensure_loaded():
    global _seen_groups, _seen_users
    if _seen_groups is None:
        _seen_groups = _load_ids(GROUPS_FILE)
        _seen_users = _load_ids(USERS_FILE)


def _append(path, id_):
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(id_ + "\n")
    except OSError:
        pass


def track_group(group_id):
    if not group_id:
        return
    _ensure_loaded()
    group_id = str(group_id).strip()
    if not group_id or group_id in _seen_groups:
        return
    _seen_groups.add(group_id)
    _append(GROUPS_FILE, group_id)


def track_user(user_id):
    if not user_id:
        return
    _ensure_loaded()
    user_id = str(user_id).strip()
    if not user_id or user_id in _seen_users:
        return
    _seen_users.add(user_id)
    _append(USERS_FILE, user_id)


def track(user_id, group_id=None):
    track_user(user_id)
    track_group(group_id)


def load_groups():
    _ensure_loaded()
    return sorted(_seen_groups)


def load_users():
    _ensure_loaded()
    return sorted(_seen_users)
