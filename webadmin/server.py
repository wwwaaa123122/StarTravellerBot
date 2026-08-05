# -*- coding: utf-8 -*-
"""StarTraveller 管理后台 - 独立 Flask 服务

独立于机器人主进程运行（不修改 client.py / main.py），按需读取机器人数据：
  - 数据文件：data/checkin、data/roles、data/rag、data/scheduled_sent.json
  - 系统状态：psutil（CPU / 内存 / 磁盘 / 进程存活检测）

启动：
    python -m webadmin.server --host 0.0.0.0 --port 8765

配置优先级（高 -> 低）：
    环境变量  STAR_TRAVELLER_ADMIN_HOST / _PORT / _PASSWORD
    config.json 中的 "webadmin" 段
    内置默认值（0.0.0.0:8765，密码 admin123）
注意：
    默认监听 0.0.0.0（所有网卡），访问时不校验 Host 头端口，请务必设置强密码。
"""

import base64
import hashlib
import hmac
import json
import os
import platform
import re
import secrets
import sys
import time
from functools import wraps

import psutil
from flask import Flask, Response, g, jsonify, request, send_from_directory

try:
    import pytz
except ImportError:  # 非必需依赖
    pytz = None

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CHECKIN_DIR = os.path.join(DATA_DIR, "checkin")
ROLES_DIR = os.path.join(DATA_DIR, "roles")
RAG_DIR = os.path.join(DATA_DIR, "rag")
PLUGINS_DIR = os.path.join(PROJECT_ROOT, "plugins")
WEBADMIN_DATA_DIR = os.path.join(DATA_DIR, "webadmin")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
SECRET_FILE = os.path.join(WEBADMIN_DATA_DIR, "secret.key")
VISITS_FILE = os.path.join(WEBADMIN_DATA_DIR, "visits.json")
CONFIG_FILE = None

VERSION = "0.1.0"

DEFAULT_ROLE_NAMES = {
    "default": "星辰旅人",
    "tsundere": "杂鱼酱",
    "cool": "冷酷助手",
}

app = Flask(__name__, static_folder=None)
app.json.ensure_ascii = False

# ---------------------------------------------------------------- 基础工具

def _read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _find_config_file():
    """按优先级查找 config.json（项目根目录 -> 父级 XCLR_QQ_bot）。"""
    candidates = [
        os.path.join(PROJECT_ROOT, "config.json"),
        os.path.join(os.path.dirname(PROJECT_ROOT), "XCLR_QQ_bot", "config.json"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def _bot_config():
    global CONFIG_FILE
    if CONFIG_FILE is None:
        CONFIG_FILE = _find_config_file()
    if not CONFIG_FILE:
        return {}
    data = _read_json(CONFIG_FILE, {}) or {}
    return data


def _admin_config():
    """管理后台自身配置（端口 / 密码等）。"""
    cfg = _bot_config().get("webadmin", {}) or {}
    return cfg


def _nickname_map():
    """读取全局昵称对照表 data/nickname_map.json（openid -> 昵称）。

    由 client.py 在收到消息事件时维护，用于展示聊天用户昵称。
    """
    data = _read_json(os.path.join(DATA_DIR, "nickname_map.json"), {}) or {}
    return data if isinstance(data, dict) else {}


def _checkin_users():
    """解析 data/checkin/*.json，返回用户列表（排除 _rank_cache.json）。

    昵称优先取签到数据，为空时回退到全局昵称对照表。
    """
    nick_map = _nickname_map()
    users = []
    if not os.path.isdir(CHECKIN_DIR):
        return users
    for name in sorted(os.listdir(CHECKIN_DIR)):
        if not name.endswith(".json") or name.startswith("_"):
            continue
        uid = name[:-5]
        data = _read_json(os.path.join(CHECKIN_DIR, name), {}) or {}
        nickname = data.get("nickname", "") or nick_map.get(uid, "") or ""
        users.append({
            "user_id": uid,
            "nickname": nickname,
            "points": int(data.get("points", 0)),
            "affection": int(data.get("affection", 0)),
            "streak": int(data.get("streak", 0)),
            "last_checkin": data.get("last_checkin", None),
        })
    users.sort(key=lambda u: u["points"], reverse=True)
    return users


# ---------------------------------------------------------------- 角色

def _load_roles():
    """加载角色数据：优先 RoleManager 的 roles.json，回退 user_roles.json。"""
    data = _read_json(os.path.join(ROLES_DIR, "roles.json"), {}) or {}
    roles = dict(DEFAULT_ROLE_NAMES)
    roles.update({rid: (r.get("name") if isinstance(r, dict) else str(r))
                  for rid, r in (data.get("roles", {}) or {}).items()})
    users = data.get("users", {}) or {}
    if not users:
        legacy = _read_json(os.path.join(ROLES_DIR, "user_roles.json"), {}) or {}
        users = {k: v for k, v in legacy.items() if not k.startswith("_")}
    return {"roles": roles, "users": users}


def _scan_plugins():
    """扫描 plugins/*.py，提取关键字与帮助信息。"""
    _kw = re.compile(r'TRIGGHT_KEYWORD\s*=\s*"([^"]*)"')
    _help = re.compile(r'HELP_MESSAGE\s*=\s*"([^"]*)"')
    plugins = []
    if not os.path.isdir(PLUGINS_DIR):
        return plugins
    for name in sorted(os.listdir(PLUGINS_DIR)):
        if not name.endswith(".py") or name.startswith("__") or name.startswith("d_"):
            continue
        path = os.path.join(PLUGINS_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception:
            continue
        kw_m = _kw.search(text)
        help_m = _help.search(text)
        plugins.append({
            "file": name,
            "keyword": kw_m.group(1) if kw_m else "",
            "help": help_m.group(1) if help_m else "",
        })
    return plugins


def _rag_records(limit=300):
    """聚合 data/rag/*.json 中的长期记忆片段。"""
    records = []
    if os.path.isdir(RAG_DIR):
        for name in sorted(os.listdir(RAG_DIR)):
            if not name.endswith(".json"):
                continue
            uid = name[:-5]
            data = _read_json(os.path.join(RAG_DIR, name), {}) or {}
            for ex in data.get("exchanges", []) or []:
                records.append({
                    "user_id": uid,
                    "question": ex.get("q", ""),
                    "answer": ex.get("a", ""),
                    "ts": ex.get("ts"),
                })
    records.sort(key=lambda r: r.get("ts") or 0, reverse=True)
    return records[:limit]


def _visit_activity(days=14):
    """按天聚合访问数据（本地文件记录，避免污染机器人数据）。"""
    data = _read_json(VISITS_FILE, {"total": 0, "hits": []}) or {}
    total = int(data.get("total", 0))
    hits = [h for h in data.get("hits", []) if isinstance(h, (int, float))]
    now = time.time()
    day = 86400
    out = []
    for i in range(days - 1, -1, -1):
        start = now - (i + 1) * day
        end = now - i * day
        out.append({
            "date": time.strftime("%m-%d", time.localtime(start)),
            "count": sum(1 for h in hits if start <= h < end),
        })
    return {"total": total, "days": out}


def _track_visit():
    """记录一次后台访问（保留最近 2000 条时间戳）。"""
    try:
        data = _read_json(VISITS_FILE, {"total": 0, "hits": []}) or {}
        data["total"] = int(data.get("total", 0)) + 1
        hits = data.get("hits", [])
        hits.append(time.time())
        data["hits"] = hits[-2000:]
        _write_json(VISITS_FILE, data)
    except Exception:
        pass


def _bot_process():
    """判断机器人主进程是否在运行。

    优先识别嵌入模式：webadmin 随 main.py 同步启动时通过环境变量
    STAR_TRAVELLER_EMBEDDED=1 标记，此时机器人必然在同一进程内运行；
    否则扫描 psutil 命令行兜底（独立启动场景）。
    """
    if os.environ.get("STAR_TRAVELLER_EMBEDDED") == "1":
        return {"running": True, "pid": os.getpid()}
    for p in psutil.process_iter(["cmdline"]):
        try:
            cmd = " ".join(p.info.get("cmdline") or [])
        except Exception:
            continue
        if "main.py" in cmd and ("StarTraveller" in cmd or "star_traveller" in cmd.lower()):
            return {"running": True, "pid": p.pid}
    return {"running": False, "pid": None}


def _system_status():
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(PROJECT_ROOT)
    try:
        proc_mem = psutil.Process().memory_info().rss / 1024 / 1024
    except Exception:
        proc_mem = 0
    return {
        "cpu_percent": round(psutil.cpu_percent(interval=0.2), 1),
        "cpu_count": psutil.cpu_count(),
        "mem_percent": round(mem.percent, 1),
        "mem_used_gb": round(mem.used / 1024 ** 3, 2),
        "mem_total_gb": round(mem.total / 1024 ** 3, 2),
        "disk_percent": round(disk.percent, 1),
        "boot_time": psutil.boot_time(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "webadmin_mem_mb": round(proc_mem, 1),
    }


def _uptime_text(seconds):
    d, r = divmod(int(seconds), 86400)
    h, r = divmod(r, 3600)
    m, _ = divmod(r, 60)
    if d:
        return f"{d}天 {h}小时 {m}分"
    if h:
        return f"{h}小时 {m}分"
    return f"{m}分"


# ---------------------------------------------------------------- 认证

def _load_secret():
    os.makedirs(WEBADMIN_DATA_DIR, exist_ok=True)
    if os.path.exists(SECRET_FILE):
        with open(SECRET_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    secret = secrets.token_hex(32)
    with open(SECRET_FILE, "w", encoding="utf-8") as f:
        f.write(secret)
    try:
        os.chmod(SECRET_FILE, 0o600)
    except Exception:
        pass
    return secret


def _signature(msg):
    return hmac.new(_load_secret().encode(), msg.encode(), hashlib.sha256).hexdigest()


def _issue_token(user, ttl=7 * 86400):
    payload = base64.urlsafe_b64encode(
        f"{user}:{int(time.time()) + ttl}".encode()
    ).decode().rstrip("=")
    return f"{payload}.{_signature(payload)}"


def _verify_token(token):
    try:
        payload, sig = token.split(".", 1)
        if not hmac.compare_digest(_signature(payload), sig):
            return None
        pad = "=" * (-len(payload) % 4)
        raw = base64.urlsafe_b64decode(payload + pad).decode()
        user, exp = raw.rsplit(":", 1)
        if int(exp) < time.time():
            return None
        return user
    except Exception:
        return None


_LOGIN_RATE = {}  # ip -> [timestamps]


def _login_rate_limit(ip):
    now = time.time()
    ts = [t for t in _LOGIN_RATE.get(ip, []) if now - t < 60]
    ts.append(now)
    _LOGIN_RATE[ip] = ts
    return len(ts) <= 10


def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip()
        user = _verify_token(token)
        if not user:
            return jsonify({"error": "unauthorized", "message": "登录已过期，请重新登录"}), 401
        g.user = user
        return f(*args, **kwargs)
    return wrapper


def admin_password():
    pwd = os.environ.get("STAR_TRAVELLER_ADMIN_PASSWORD") or _admin_config().get("password")
    if pwd:
        return pwd
    return "admin123"


# ---------------------------------------------------------------- API

@app.get("/admin/api/ping")
def api_ping():
    return jsonify({"ok": True, "name": "StarTraveller 管理后台", "version": VERSION})


@app.post("/admin/api/login")
def api_login():
    ip = request.remote_addr or "?"
    if not _login_rate_limit(ip):
        return jsonify({"error": "too_many", "message": "尝试过于频繁，请 1 分钟后再试"}), 429
    body = request.get_json(silent=True) or {}
    if hmac.compare_digest(str(body.get("password", "")), admin_password()):
        token = _issue_token("admin")
        return jsonify({"token": token, "expires_in": 7 * 86400})
    return jsonify({"error": "bad_password", "message": "密码错误"}), 401


@app.get("/admin/api/overview")
@require_auth
def api_overview():
    _track_visit()
    users = _checkin_users()
    today = time.strftime("%Y-%m-%d")
    today_checked = sum(1 for u in users if u["last_checkin"] == today)
    total_points = sum(u["points"] for u in users)
    roles = _load_roles()
    role_dist = {}
    for uid, rid in roles["users"].items():
        role_dist[roles["roles"].get(rid, rid)] = role_dist.get(roles["roles"].get(rid, rid), 0) + 1

    # 近 14 天签到趋势
    from datetime import datetime, timedelta
    days = []
    for i in range(13, -1, -1):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        days.append({
            "date": d[5:],
            "count": sum(1 for u in users if u["last_checkin"] == d),
        })

    visit = _visit_activity(14)
    bot = _bot_process()
    return jsonify({
        "stats": {
            "users": len(users),
            "today_checked": today_checked,
            "total_points": total_points,
            "roles": len(role_dist),
            "rag_count": len(_rag_records(10 ** 9)),
            "plugins": len(_scan_plugins()),
            "visits": visit["total"],
            "last_checkin": max((u["last_checkin"] for u in users if u["last_checkin"]), default=None),
        },
        "trend": days,
        "activity": visit["days"],
        "role_distribution": [{"name": k, "value": v} for k, v in sorted(role_dist.items(), key=lambda x: -x[1])],
        "top_users": users[:8],
        "bot": bot,
    })


@app.get("/admin/api/status")
@require_auth
def api_status():
    sys_stat = _system_status()
    sys_stat["uptime_text"] = _uptime_text(time.time() - sys_stat["boot_time"])
    return jsonify({"status": sys_stat, "bot": _bot_process()})


@app.get("/admin/api/users")
@require_auth
def api_users():
    users = _checkin_users()
    roles = _load_roles()
    role_names = roles["roles"]
    for u in users:
        u["role"] = role_names.get(roles["users"].get(u["user_id"]), "默认")
    rank_cache = _read_json(os.path.join(CHECKIN_DIR, "_rank_cache.json"), {}) or {}
    return jsonify({"users": users, "rank_meta": rank_cache if isinstance(rank_cache, dict) else {}})


@app.get("/admin/api/memory")
@require_auth
def api_memory():
    records = _rag_records(500)
    user_ids = sorted({r["user_id"] for r in records})
    return jsonify({"records": records, "users": user_ids})


@app.get("/admin/api/plugins")
@require_auth
def api_plugins():
    return jsonify({"plugins": _scan_plugins()})


@app.get("/admin/api/schedule")
@require_auth
def api_schedule():
    cfg = _bot_config()
    sched = cfg.get("scheduled_send", {}) or {}
    sent = _read_json(os.path.join(DATA_DIR, "scheduled_sent.json"), {}) or {}
    last = sent.get("date")
    today = time.strftime("%Y-%m-%d")
    if last == today:
        today_done = True
    else:
        today_done = False
    return jsonify({
        "enabled": bool(sched.get("enabled", True)),
        "send_time": sched.get("send_time", "08:30"),
        "channels": sched.get("channels", []),
        "content": sched.get("content", ""),
        "last_sent": last,
        "today_done": today_done,
    })


@app.get("/admin/api/config")
@require_auth
def api_config():
    cfg = _bot_config()
    masked = _mask_dict(cfg)
    bot_info = {
        "name": cfg.get("bot_name") or cfg.get("Others", {}).get("bot_name"),
        "log_level": cfg.get("Log_level") or cfg.get("log_level"),
        "sandbox": cfg.get("is_sandbox"),
        "openqq_appid": cfg.get("appid") or cfg.get("openqq", {}).get("appid"),
        "config_path": CONFIG_FILE,
    }
    return jsonify({"config": masked, "bot_info": bot_info, "version": VERSION})


_SENSITIVE = ("password", "secret", "token", "key", "appid", "appsecret", "api")


def _mask_value(v):
    s = str(v)
    if len(s) <= 6:
        return "******"
    return s[:3] + "*" * 8 + s[-2:]


def _mask_dict(obj, depth=0):
    if depth > 3:
        return obj
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if isinstance(v, (dict, list)) and not isinstance(v, str):
                out[k] = _mask_dict(v, depth + 1)
            elif any(t in k.lower() for t in _SENSITIVE):
                out[k] = _mask_value(v)
            else:
                out[k] = v
        return out
    if isinstance(obj, list):
        return [_mask_dict(x, depth + 1) if isinstance(x, (dict, list)) else x for x in obj]
    return obj


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "not_found"}), 404


@app.errorhandler(Exception)
def server_error(e):
    app.logger.exception("webadmin error")
    return jsonify({"error": "internal", "message": str(e)}), 500


# ---------------------------------------------------------------- 静态页面

@app.get("/admin")
def admin_index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/admin/static/<path:filename>")
def admin_static(filename):
    return send_from_directory(STATIC_DIR, filename)


def _resolve_admin_addr(host=None, port=None):
    """解析管理后台监听地址：参数 > 环境变量 > config.json webadmin 段 > 默认值。"""
    host = host or os.environ.get("STAR_TRAVELLER_ADMIN_HOST") \
        or _admin_config().get("host") or "0.0.0.0"
    port = port or int(os.environ.get("STAR_TRAVELLER_ADMIN_PORT") or 0) \
        or int(_admin_config().get("port") or 0) or 8765
    return host, port


def _print_banner(host, port):
    if host in ("0.0.0.0", "::"):
        addr = "http://服务器IP:%d/admin" % port
    else:
        addr = "http://%s:%d/admin" % (host, port)
    print("StarTraveller 管理后台 v%s  %s" % (VERSION, addr))


def start_server(host=None, port=None, password=None):
    """以守护线程启动管理后台，供 main.py 同步启动调用（不阻塞机器人事件循环）。

    参数优先级：显式参数 > 环境变量 > config.json 的 webadmin 段 > 默认值。
    成功返回后台线程对象；端口占用等失败场景返回 None（不中断机器人）。
    """
    import threading
    from werkzeug.serving import make_server

    host, port = _resolve_admin_addr(host, port)
    if password:
        os.environ["STAR_TRAVELLER_ADMIN_PASSWORD"] = password
    os.environ["STAR_TRAVELLER_EMBEDDED"] = "1"

    try:
        server = make_server(host, port, app, threaded=True)
    except (OSError, SystemExit) as exc:
        print(f"[webadmin] 启动失败: {exc}", file=sys.stderr)
        return None

    thread = threading.Thread(
        target=server.serve_forever,
        name="webadmin-server",
        daemon=True,
    )
    thread.start()
    _print_banner(host, port)
    return thread


def main():
    import argparse

    parser = argparse.ArgumentParser(description="StarTraveller 管理后台")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()

    host, port = _resolve_admin_addr(args.host, args.port)
    _print_banner(host, port)
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
