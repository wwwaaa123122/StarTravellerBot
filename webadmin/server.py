# -*- coding: utf-8 -*-

import base64
import hashlib
import hmac
import json
import os
import platform
import re
import secrets
import sqlite3
import sys
import time
from functools import wraps

import qqbot_openapi.psutil_compat as psutil
from flask import Flask, Response, g, jsonify, request, send_from_directory

try:
    import pytz
except ImportError:
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
STATS_FILE = os.path.join(DATA_DIR, "stats.json")
PLUGINS_ENABLED_FILE = os.path.join(DATA_DIR, "plugins_enabled.json")
PROMPTS_FILE = os.path.join(DATA_DIR, "prompts.json")
ENV_FILE = os.path.join(PROJECT_ROOT, ".env")

VERSION = "0.1.0"

DEFAULT_ROLE_NAMES = {
    "default": "星辰旅人",
    "tsundere": "杂鱼酱",
    "cool": "冷酷助手",
}

app = Flask(__name__, static_folder=None)
app.json.ensure_ascii = False


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


def _write_env(pairs: dict):
    lines = []
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
    out = []
    written = set()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.partition("=")[0].strip()
            if key in pairs:
                out.append(f"{key}={pairs[key]}\n")
                written.add(key)
                continue
        out.append(line)
    for key, value in pairs.items():
        if key not in written:
            out.append(f"{key}={value}\n")
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(out)


def _bot_config():
    from config import load_settings
    return load_settings().data


def _admin_config():
    cfg = _bot_config().get("webadmin", {}) or {}
    return cfg


def _nickname_map():
    data = _read_json(os.path.join(DATA_DIR, "nickname_map.json"), {}) or {}
    return data if isinstance(data, dict) else {}


def _checkin_users():
    nick_map = _nickname_map()
    db_path = os.path.join(DATA_DIR, "checkin.db")
    if not os.path.exists(db_path):
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    users = []
    for row in conn.execute("SELECT * FROM checkin ORDER BY points DESC"):
        nickname = row["nickname"] or nick_map.get(row["user_id"], "") or ""
        users.append({
            "user_id": row["user_id"],
            "nickname": str(nickname),
            "points": int(row["points"]),
            "affection": int(row["affection"]),
            "streak": int(row["streak"]),
            "last_checkin": row["last_checkin"],
        })
    conn.close()
    return users


def _load_roles():
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
    _kw = re.compile(r'TRIG(?:GER|GHT)_KEYWORD\s*=\s*"([^"]*)"')
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


def _read_stats():
    default = {
        "total_messages": 0,
        "messages_today": {"date": time.strftime("%Y-%m-%d"), "count": 0},
        "total_ai_calls": 0,
        "ai_calls_today": {"date": time.strftime("%Y-%m-%d"), "count": 0},
        "total_tokens": 0,
        "tokens_today": {"date": time.strftime("%Y-%m-%d"), "count": 0},
    }
    data = _read_json(STATS_FILE, default) or default
    today = time.strftime("%Y-%m-%d")
    for key in ("messages_today", "ai_calls_today", "tokens_today"):
        if data.get(key, {}).get("date") != today:
            data[key] = {"date": today, "count": 0}
    return data


def _read_plugins_enabled():
    return _read_json(PLUGINS_ENABLED_FILE, {}) or {}


def _read_ai_stats():
    data = _read_json(os.path.join(DATA_DIR, "ai_stats.json"), {}) or {}
    requests = data.get("requests", 0)
    data["avg_latency"] = round(data.get("latency_sum", 0) / requests, 2) if requests else 0.0
    data["error_rate"] = round(data.get("errors", 0) / requests, 4) if requests else 0.0
    data["total_tokens"] = data.get("prompt_tokens", 0) + data.get("completion_tokens", 0)
    data["cost"] = round(data.get("cost", 0), 4)
    return data


def _read_prompts():
    return _read_json(PROMPTS_FILE, {"prompts": {}}) or {"prompts": {}}


def _uptime_text(seconds):
    d, r = divmod(int(seconds), 86400)
    h, r = divmod(r, 3600)
    m, _ = divmod(r, 60)
    if d:
        return f"{d}天 {h}小时 {m}分"
    if h:
        return f"{h}小时 {m}分"
    return f"{m}分"



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


_LOGIN_RATE = {}


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
    bot_stats = _read_stats()
    ai_stats = _read_ai_stats()
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
            "total_messages": bot_stats["total_messages"],
            "messages_today": bot_stats["messages_today"]["count"],
            "total_ai_calls": bot_stats["total_ai_calls"],
            "ai_calls_today": bot_stats["ai_calls_today"]["count"],
            "total_tokens": bot_stats["total_tokens"],
            "tokens_today": bot_stats["tokens_today"]["count"],
        },
        "ai_stats": {
            "requests": ai_stats.get("requests", 0),
            "total_tokens": ai_stats.get("total_tokens", 0),
            "avg_latency": ai_stats.get("avg_latency", 0),
            "error_rate": ai_stats.get("error_rate", 0),
            "cost": ai_stats.get("cost", 0),
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
    rank_meta = {}
    db_path = os.path.join(DATA_DIR, "checkin.db")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        for row in conn.execute("SELECT last_checkin, COUNT(*) as cnt FROM checkin WHERE last_checkin IS NOT NULL GROUP BY last_checkin"):
            rank_meta[row["last_checkin"]] = row["cnt"]
        conn.close()
    return jsonify({"users": users, "rank_meta": rank_meta})


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
        "config_path": ENV_FILE,
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



@app.get("/admin/api/stats")
@require_auth
def api_stats():
    return jsonify({"stats": _read_stats()})


@app.post("/admin/api/stats/reset")
@require_auth
def api_stats_reset():
    default = {
        "total_messages": 0,
        "messages_today": {"date": time.strftime("%Y-%m-%d"), "count": 0},
        "total_ai_calls": 0,
        "ai_calls_today": {"date": time.strftime("%Y-%m-%d"), "count": 0},
        "total_tokens": 0,
        "tokens_today": {"date": time.strftime("%Y-%m-%d"), "count": 0},
    }
    _write_json(STATS_FILE, default)
    return jsonify({"ok": True, "stats": default})



@app.get("/admin/api/permissions")
@require_auth
def api_permissions():
    cfg = _bot_config()
    others = cfg.get("Others", {})
    return jsonify({
        "root_users": others.get("ROOT_User", []),
        "blacklist": cfg.get("black_list", []),
        "allow_ai": others.get("allow_ai", True),
    })


@app.put("/admin/api/permissions")
@require_auth
def api_permissions_put():
    body = request.get_json(silent=True) or {}
    pairs = {}
    if "root_users" in body:
        pairs["STAR_BOT_ROOT_USER"] = ",".join(body["root_users"] or [])
    if "blacklist" in body:
        pairs["STAR_BLACK_LIST"] = ",".join(body["blacklist"] or [])
    if "allow_ai" in body:
        pairs["STAR_BOT_ALLOW_AI"] = "true" if body["allow_ai"] else "false"
    _write_env(pairs)
    return jsonify({"ok": True})



@app.get("/admin/api/plugins/toggle")
@require_auth
def api_plugins_toggle():
    enabled = _read_plugins_enabled()
    all_plugins = _scan_plugins()
    result = []
    for p in all_plugins:
        plugin_name = p["file"].replace(".py", "")
        result.append({
            "name": plugin_name,
            "file": p["file"],
            "keyword": p["keyword"],
            "help": p["help"],
            "enabled": enabled.get(plugin_name, True),
        })
    return jsonify({"plugins": result})


@app.put("/admin/api/plugins/toggle")
@require_auth
def api_plugins_toggle_put():
    body = request.get_json(silent=True) or {}
    enabled = _read_plugins_enabled()
    for name, state in body.items():
        if isinstance(state, bool):
            enabled[name] = state
    _write_json(PLUGINS_ENABLED_FILE, enabled)
    _write_json(os.path.join(DATA_DIR, "reload.flag"), {"ts": time.time()})
    return jsonify({"ok": True, "plugins": enabled})



@app.get("/admin/api/ai-settings")
@require_auth
def api_ai_settings():
    cfg = _bot_config()
    others = cfg.get("Others", {})
    return jsonify({
        "ai_model": others.get("ai_model", "deepseek-v4-flash"),
        "ai_base_url": others.get("ai_base_url", "https://api.deepseek.com"),
        "ai_max_tokens": others.get("ai_max_tokens", 2000),
        "ai_temperature": others.get("ai_temperature", 0.7),
        "deepseek_key": _mask_value(others.get("deepseek_key", "")),
        "gemini_key": _mask_value(others.get("gemini_key", "")),
        "openai_key": _mask_value(others.get("openai_key", "")),
        "enable_network": others.get("EnableNetwork", "DeepSeek"),
    })


@app.put("/admin/api/ai-settings")
@require_auth
def api_ai_settings_put():
    body = request.get_json(silent=True) or {}
    field_map = {
        "ai_model": "STAR_AI_MODEL",
        "ai_base_url": "STAR_AI_BASE_URL",
        "ai_max_tokens": "STAR_AI_MAX_TOKENS",
        "ai_temperature": "STAR_AI_TEMPERATURE",
        "deepseek_key": "STAR_DEEPSEEK_KEY",
        "gemini_key": "STAR_GEMINI_KEY",
        "openai_key": "STAR_OPENAI_KEY",
        "EnableNetwork": "STAR_BOT_DEFAULT_MODE",
    }
    pairs = {}
    for field, env_key in field_map.items():
        val = body.get(field)
        if val is None or str(val).startswith("***"):
            continue
        pairs[env_key] = str(val)
    _write_env(pairs)
    return jsonify({"ok": True})



@app.get("/admin/api/prompts")
@require_auth
def api_prompts():
    return jsonify(_read_prompts())


@app.post("/admin/api/prompts")
@require_auth
def api_prompts_create():
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    content = (body.get("content") or "").strip()
    if not name or not content:
        return jsonify({"error": "bad_request", "message": "名称和内容不能为空"}), 400
    data = _read_prompts()
    if name in data["prompts"]:
        return jsonify({"error": "conflict", "message": "Prompt '" + name + "' 已存在"}), 409
    data["prompts"][name] = {
        "content": content,
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    _write_json(PROMPTS_FILE, data)
    return jsonify({"ok": True, "prompt": data["prompts"][name]})


@app.put("/admin/api/prompts/<name>")
@require_auth
def api_prompts_update(name):
    body = request.get_json(silent=True) or {}
    content = (body.get("content") or "").strip()
    if not content:
        return jsonify({"error": "bad_request", "message": "内容不能为空"}), 400
    data = _read_prompts()
    if name not in data["prompts"]:
        return jsonify({"error": "not_found", "message": "Prompt '" + name + "' 不存在"}), 404
    data["prompts"][name]["content"] = content
    data["prompts"][name]["updated_at"] = time.time()
    _write_json(PROMPTS_FILE, data)
    return jsonify({"ok": True, "prompt": data["prompts"][name]})


@app.delete("/admin/api/prompts/<name>")
@require_auth
def api_prompts_delete(name):
    data = _read_prompts()
    if name not in data["prompts"]:
        return jsonify({"error": "not_found", "message": "Prompt '" + name + "' 不存在"}), 404
    del data["prompts"][name]
    _write_json(PROMPTS_FILE, data)
    return jsonify({"ok": True})


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "not_found"}), 404


@app.errorhandler(Exception)
def server_error(e):
    app.logger.exception("webadmin error")
    return jsonify({"error": "internal", "message": str(e)}), 500



@app.get("/admin")
def admin_index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/admin/static/<path:filename>")
def admin_static(filename):
    return send_from_directory(STATIC_DIR, filename)


def _resolve_admin_addr(host=None, port=None):
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
