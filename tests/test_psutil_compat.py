# -*- coding: utf-8 -*-
"""psutil_compat 纯 Python 实现测试（强制纯模式，覆盖 Termux/Android 场景）。"""

import importlib
import os
import sys
import time

import pytest

pytestmark = pytest.mark.skipif(
    not (sys.platform.startswith("linux") or sys.platform == "android"),
    reason="纯 Python 实现仅支持 Linux/Android（依赖 /proc）",
)


@pytest.fixture()
def pure_psutil(monkeypatch):
    monkeypatch.setenv("PSUTIL_COMPAT_PURE", "1")
    mod = importlib.import_module("qqbot_openapi.psutil_compat")
    return importlib.reload(mod)


def test_cpu_percent_interval(pure_psutil):
    v = pure_psutil.cpu_percent(interval=0.05)
    assert isinstance(v, float)
    assert 0.0 <= v <= 100.0


def test_cpu_percent_no_interval(pure_psutil):
    first = pure_psutil.cpu_percent()
    assert isinstance(first, float)
    second = pure_psutil.cpu_percent()
    assert isinstance(second, float)
    assert 0.0 <= second <= 100.0


def test_virtual_memory(pure_psutil):
    mem = pure_psutil.virtual_memory()
    assert mem.total > 0
    assert mem.available >= 0
    assert mem.used >= 0
    assert 0.0 <= mem.percent <= 100.0


def test_disk_usage(pure_psutil):
    d = pure_psutil.disk_usage("/")
    assert d.total > 0
    assert d.used >= 0
    assert d.free >= 0
    assert 0.0 <= d.percent <= 100.0


def test_cpu_count(pure_psutil):
    assert pure_psutil.cpu_count() >= 1
    assert pure_psutil.cpu_count(logical=False) >= 1


def test_boot_time(pure_psutil):
    bt = pure_psutil.boot_time()
    assert isinstance(bt, float)
    assert 0 < bt <= time.time()


def test_process_iter_and_info(pure_psutil):
    pids = [p.pid for p in pure_psutil.process_iter(["cmdline"])]
    assert os.getpid() in pids
    for p in pure_psutil.process_iter(["cmdline"]):
        if p.pid == os.getpid():
            assert isinstance(p.info, dict)
            cmd = " ".join(p.info.get("cmdline") or [])
            assert "python" in cmd.lower() or "pytest" in cmd.lower()


def test_process_memory_info(pure_psutil):
    mi = pure_psutil.Process().memory_info()
    assert mi.rss > 0
    assert isinstance(mi.rss, int)


def test_process_cmdline(pure_psutil):
    cmd = pure_psutil.Process().cmdline()
    assert isinstance(cmd, list)
    assert cmd


def test_public_api_shape(pure_psutil):
    for name in ("cpu_percent", "cpu_count", "virtual_memory",
                 "disk_usage", "boot_time", "process_iter", "Process"):
        assert callable(getattr(pure_psutil, name)), name
