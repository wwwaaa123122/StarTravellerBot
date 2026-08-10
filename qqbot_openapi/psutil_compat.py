# -*- coding: utf-8 -*-

import logging
import os
import sys
import time
from collections import namedtuple

__version__ = "1.0.0"

logger = logging.getLogger("qqbot_openapi.psutil_compat")

svmem = namedtuple(
    "svmem",
    ["total", "available", "percent", "used", "free",
     "active", "inactive", "buffers", "cached", "shared", "slab"],
)
sdiskusage = namedtuple("sdiskusage", ["total", "used", "free", "percent"])
pfullmem = namedtuple(
    "pfullmem",
    ["rss", "vms", "shared", "text", "lib", "data", "dirty"],
)

_PROC = "/proc"

_IS_ANDROID = bool(
    os.environ.get("ANDROID_ROOT")
    or os.path.exists("/system/build.prop")
    or os.environ.get("PREFIX", "").startswith("/data/data/com.termux")
)

_FORCE_PURE = os.environ.get("PSUTIL_COMPAT_PURE", "").strip().lower() in ("1", "true", "yes", "force")
_DEBUG = os.environ.get("PSUTIL_COMPAT_DEBUG", "").strip().lower() in ("1", "true", "yes")

_real = None
try:
    import psutil as _real
except Exception:
    _real = None

if _FORCE_PURE:
    _USE_REAL = False
    _log_reason = "PSUTIL_COMPAT_PURE=1，强制纯 Python 实现"
elif _IS_ANDROID:
    _USE_REAL = False
    _log_reason = "Android/Termux 环境，使用纯 Python 实现（避免 psutil 编译/运行问题）"
elif _real is not None:
    _USE_REAL = True
    _log_reason = "已安装 psutil 且非 Android，委托给真实 psutil"
else:
    _USE_REAL = False
    _log_reason = "psutil 未安装，使用纯 Python 实现"

_PURE_OK = sys.platform.startswith("linux") or sys.platform == "android"


def _log(msg):
    if _DEBUG:
        print(f"[psutil_compat] {msg}", file=sys.stderr)
    logger.debug(msg)


_log(_log_reason)

_warned = set()


def _warn_once(key, msg):
    if key not in _warned:
        _warned.add(key)
        logger.warning(msg, exc_info=True)
    else:
        logger.debug(msg)


def _ensure_pure():
    if not _PURE_OK:
        raise RuntimeError(
            "qqbot_openapi.psutil_compat 纯 Python 实现仅支持 Linux/Android，"
            "当前平台请安装 psutil：pip install psutil"
        )


_last_cpu = None


def _parse_cpu_line(line):
    nums = [int(p) for p in line.split()[1:]]
    while len(nums) < 10:
        nums.append(0)
    user, nice, system, idle, iowait, irq, softirq, steal, guest, guest_nice = nums[:10]
    user -= guest
    nice -= guest_nice
    total = user + nice + system + idle + iowait + irq + softirq + steal + guest + guest_nice
    return total, total - idle - iowait


def _read_cpu_times():
    with open(os.path.join(_PROC, "stat"), "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("cpu "):
                return _parse_cpu_line(line)
    raise OSError("无法解析 /proc/stat 中的 cpu 行")


def _pure_cpu_percent(interval=None):
    _ensure_pure()
    global _last_cpu
    try:
        if interval is not None:
            before = _read_cpu_times()
            time.sleep(interval)
            after = _read_cpu_times()
        else:
            before = _last_cpu
            after = _read_cpu_times()
            if before is None:
                _last_cpu = after
                return 0.0
        total_delta = after[0] - before[0]
        busy_delta = after[1] - before[1]
        _last_cpu = after
        if total_delta <= 0:
            return 0.0
        return round(min(100.0, max(0.0, (busy_delta / total_delta) * 100.0)), 1)
    except Exception:
        _warn_once("cpu", "psutil_compat: cpu_percent 读取失败（Android 上 /proc/stat 常被 SELinux 拒绝，返回 0.0）")
        return 0.0


def _pure_cpu_count(logical=True):
    _ensure_pure()
    try:
        if logical:
            n = os.cpu_count()
            return n if n else 1
        cores = set()
        with open(os.path.join(_PROC, "cpuinfo"), "r", encoding="utf-8") as f:
            for line in f:
                if line.lower().startswith("core id"):
                    cores.add(line.split(":", 1)[1].strip())
        if cores:
            return len(cores)
        n = os.cpu_count()
        return n if n else 1
    except Exception:
        n = os.cpu_count()
        return n if n else 1


def _read_meminfo():
    data = {}
    with open(os.path.join(_PROC, "meminfo"), "r", encoding="utf-8") as f:
        for line in f:
            key, _, rest = line.partition(":")
            rest = rest.strip()
            if not rest:
                continue
            try:
                val = int(rest.split()[0])
            except ValueError:
                continue
            data[key.strip()] = val * 1024 if rest.endswith("kB") else val
    return data


def _pure_virtual_memory():
    _ensure_pure()
    try:
        d = _read_meminfo()
        total = d.get("MemTotal", 0)
        free = d.get("MemFree", 0)
        if "MemAvailable" in d:
            available = d.get("MemAvailable", 0)
            used = max(total - available, 0)
        else:
            available = free + d.get("Buffers", 0) + d.get("Cached", 0)
            used = max(total - free - d.get("Buffers", 0) - d.get("Cached", 0), 0)
        percent = round((used / total) * 100.0, 1) if total else 0.0
        return svmem(
            total=total,
            available=available,
            percent=percent,
            used=used,
            free=free,
            active=d.get("Active", 0),
            inactive=d.get("Inactive", 0),
            buffers=d.get("Buffers", 0),
            cached=d.get("Cached", 0),
            shared=d.get("Shmem", 0),
            slab=d.get("SReclaimable", 0) + d.get("SUnreclaim", 0),
        )
    except Exception:
        _warn_once("mem", "psutil_compat: virtual_memory 读取失败")
        return svmem(0, 0, 0.0, 0, 0, 0, 0, 0, 0, 0, 0)


def _pure_disk_usage(path):
    _ensure_pure()
    try:
        st = os.statvfs(path)
        total = st.f_blocks * st.f_frsize
        free = st.f_bfree * st.f_frsize
        used = total - free
        percent = round((used / total) * 100.0, 1) if total else 0.0
        return sdiskusage(total, used, free, percent)
    except Exception:
        _warn_once("disk", "psutil_compat: disk_usage(%r) 读取失败" % (path,))
        return sdiskusage(0, 0, 0, 0.0)


_boot_time_cache = None


def _pure_boot_time():
    _ensure_pure()
    global _boot_time_cache
    if _boot_time_cache is not None:
        return _boot_time_cache
    try:
        try:
            with open(os.path.join(_PROC, "stat"), "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("btime"):
                        _boot_time_cache = float(line.split()[1])
                        return _boot_time_cache
        except OSError:
            pass
        with open(os.path.join(_PROC, "uptime"), "r", encoding="utf-8") as f:
            uptime = float(f.read().split()[0])
        _boot_time_cache = time.time() - uptime
        return _boot_time_cache
    except Exception:
        _warn_once("boot", "psutil_compat: boot_time 读取失败（/proc/stat、/proc/uptime 均不可读，返回当前时间）")
        return time.time()


def _iter_pids():
    pids = []
    try:
        for name in os.listdir(_PROC):
            if name.isdigit():
                try:
                    pids.append(int(name))
                except ValueError:
                    pass
    except OSError:
        pass
    pids.sort()
    return pids


class _Process:

    def __init__(self, pid=None):
        self._pid = os.getpid() if pid is None else int(pid)
        self._info = None

    @property
    def pid(self):
        return self._pid

    @property
    def info(self):
        return self._info if self._info is not None else {}

    def _path(self, name):
        return os.path.join(_PROC, str(self._pid), name)

    def _read(self, name, default=b""):
        try:
            with open(self._path(name), "rb") as f:
                return f.read()
        except Exception:
            return default

    def cmdline(self):
        raw = self._read("cmdline")
        if not raw:
            return []
        return [p.decode("utf-8", "replace") for p in raw.split(b"\x00") if p]

    def memory_info(self):
        try:
            page = os.sysconf("SC_PAGE_SIZE")
        except Exception:
            page = 4096
        rss = vms = shared = 0
        try:
            parts = self._read("statm").split()
            if len(parts) >= 3:
                vms = int(parts[0]) * page
                rss = int(parts[1]) * page
                shared = int(parts[2]) * page
        except Exception:
            status = self._read("status").decode("utf-8", "replace")
            for line in status.splitlines():
                if line.startswith("VmRSS:"):
                    rss = int(line.split()[1]) * 1024
                elif line.startswith("VmSize:"):
                    vms = int(line.split()[1]) * 1024
        return pfullmem(rss, vms, shared, 0, 0, 0, 0)


def _pure_process_iter(attrs=None, ad_value=None):
    _ensure_pure()
    for pid in _iter_pids():
        p = _Process(pid)
        if attrs:
            info = {}
            for name in attrs:
                try:
                    info[name] = getattr(p, name)()
                except Exception:
                    info[name] = ad_value
            p._info = info
        yield p


def cpu_percent(interval=None):
    if _USE_REAL:
        return _real.cpu_percent(interval=interval)
    return _pure_cpu_percent(interval)


def cpu_count(logical=True):
    if _USE_REAL:
        return _real.cpu_count(logical=logical)
    return _pure_cpu_count(logical)


def virtual_memory():
    if _USE_REAL:
        return _real.virtual_memory()
    return _pure_virtual_memory()


def disk_usage(path):
    if _USE_REAL:
        return _real.disk_usage(path)
    return _pure_disk_usage(path)


def boot_time():
    if _USE_REAL:
        return _real.boot_time()
    return _pure_boot_time()


def process_iter(attrs=None, ad_value=None):
    if _USE_REAL:
        return _real.process_iter(attrs=attrs, ad_value=ad_value)
    return _pure_process_iter(attrs=attrs, ad_value=ad_value)


def Process(pid=None):
    if _USE_REAL:
        return _real.Process(pid)
    return _Process(pid)


__all__ = [
    "__version__",
    "cpu_percent",
    "cpu_count",
    "virtual_memory",
    "disk_usage",
    "boot_time",
    "process_iter",
    "Process",
]
