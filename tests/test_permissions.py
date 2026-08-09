# -*- coding: utf-8 -*-
"""权限判定测试：黑名单 / ROOT_User。"""

from core.permissions import is_blacklisted, is_root


def test_blacklisted():
    config = {"black_list": ["u1"]}
    assert is_blacklisted("u1", config) is True
    assert is_blacklisted("u2", config) is False
    assert is_blacklisted("u1", {}) is False


def test_is_root():
    config = {"Others": {"ROOT_User": ["admin1"]}}
    assert is_root("admin1", config) is True
    assert is_root("nobody", config) is False
    assert is_root("admin1", {}) is False
