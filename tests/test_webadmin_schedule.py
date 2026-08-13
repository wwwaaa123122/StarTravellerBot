# -*- coding: utf-8 -*-

import os

import pytest


@pytest.fixture
def ws(monkeypatch, tmp_path):
    """隔离 webadmin 的 .env / data 路径，避免测试污染项目文件。"""
    import core.usage_tracker as UT
    import webadmin.server as S

    data_dir = str(tmp_path / "data")
    monkeypatch.setattr(S, "ENV_FILE", str(tmp_path / ".env"))
    monkeypatch.setattr(S, "DATA_DIR", data_dir)
    monkeypatch.setattr(S, "WEBADMIN_DATA_DIR", os.path.join(data_dir, "webadmin"))
    monkeypatch.setattr(S, "SECRET_FILE", os.path.join(data_dir, "webadmin", "secret.key"))
    monkeypatch.setattr(S, "VISITS_FILE", os.path.join(data_dir, "webadmin", "visits.json"))
    monkeypatch.setattr(S, "STATS_FILE", os.path.join(data_dir, "stats.json"))
    monkeypatch.setattr(S, "PLUGINS_ENABLED_FILE", os.path.join(data_dir, "plugins_enabled.json"))
    monkeypatch.setattr(S, "PROMPTS_FILE", os.path.join(data_dir, "prompts.json"))

    for key in ("STAR_SCHEDULED_SEND_TIME", "STAR_SCHEDULED_SEND_CONTENT",
                "STAR_SCHEDULED_SEND_GROUPS", "STAR_SCHEDULED_SEND_ADMIN",
                "STAR_SCHEDULED_SEND_ENABLED", "STAR_TRAVELLER_ADMIN_PASSWORD"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(S, "admin_password", lambda: "admin123")

    monkeypatch.setattr(UT, "DATA_DIR", data_dir)
    monkeypatch.setattr(UT, "GROUPS_FILE", os.path.join(data_dir, "groups_list.txt"))
    monkeypatch.setattr(UT, "USERS_FILE", os.path.join(data_dir, "users_list.txt"))
    UT._seen_groups = None
    UT._seen_users = None

    S.app.testing = True
    client = S.app.test_client()
    r = client.post("/admin/api/login", json={"password": "admin123"})
    assert r.status_code == 200
    headers = {"Authorization": "Bearer " + r.get_json()["token"]}
    return S, client, headers, tmp_path


def test_schedule_get_uses_default_content_and_groups(ws):
    S, client, headers, _ = ws
    r = client.get("/admin/api/schedule", headers=headers)
    assert r.status_code == 200
    d = r.get_json()
    assert d["content"] == "早生蚝"
    assert d["send_time"] == "06:00"
    assert d["channels"] == []
    assert d["enabled"] is True


def test_schedule_put_writes_env_and_trigger_reload(ws):
    S, client, headers, tmp_path = ws
    r = client.put("/admin/api/schedule", headers=headers, json={
        "enabled": True,
        "send_time": "09:15",
        "content": "早中蚝",
        "groups": ["g_a", "g_b"],
        "admin_user": "u_admin",
    })
    assert r.status_code == 200

    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "STAR_SCHEDULED_SEND_TIME=09:15" in env_text
    assert "STAR_SCHEDULED_SEND_GROUPS=g_a,g_b" in env_text
    assert "STAR_SCHEDULED_SEND_CONTENT=早中蚝" in env_text
    assert os.environ.get("STAR_SCHEDULED_SEND_TIME") == "09:15"
    assert os.path.exists(os.path.join(S.DATA_DIR, "reload.flag"))

    # 重新读取配置应反映新值
    d = client.get("/admin/api/schedule", headers=headers).get_json()
    assert d["send_time"] == "09:15"
    assert d["content"] == "早中蚝"
    assert d["channels"] == ["g_a", "g_b"]


def test_schedule_put_rejects_bad_time(ws):
    S, client, headers, _ = ws
    r = client.put("/admin/api/schedule", headers=headers, json={"send_time": "25:99"})
    assert r.status_code == 400
    r = client.put("/admin/api/schedule", headers=headers, json={"send_time": "9:5"})
    assert r.status_code == 400


def test_schedule_send_bot_offline(ws):
    S, client, headers, _ = ws
    from Tools.scheduler import get_loop, set_client

    # 保存现场，将 client/loop 置空模拟 bot 未运行
    saved = None
    set_client(saved)
    assert get_loop() is None
    r = client.post("/admin/api/schedule/send", headers=headers, json={"content": "hi"})
    assert r.status_code == 400
    assert r.get_json()["error"] == "bot_offline"


def test_schedule_send_no_content(ws):
    S, client, headers, _ = ws
    from Tools.scheduler import set_client

    set_client(None)
    r = client.post("/admin/api/schedule/send", headers=headers, json={"content": "", "groups": []})
    assert r.status_code == 400


def test_usage_tracker_writes_list_files(ws):
    S, client, headers, tmp_path = ws
    from core.usage_tracker import load_groups, load_users, track

    track("user_1", "group_1")
    track("user_2", "group_1")
    track("user_2", "group_2")

    groups_file = tmp_path / "data" / "groups_list.txt"
    users_file = tmp_path / "data" / "users_list.txt"
    assert groups_file.exists()
    assert users_file.exists()
    assert groups_file.read_text(encoding="utf-8").split() == ["group_1", "group_2"]
    assert users_file.read_text(encoding="utf-8").split() == ["user_1", "user_2"]

    assert load_groups() == ["group_1", "group_2"]
    assert load_users() == ["user_1", "user_2"]

    # 重复记录不重复写入
    track("user_1", "group_1")
    assert len(users_file.read_text(encoding="utf-8").split()) == 2

    # API 返回列表
    r = client.get("/admin/api/usage", headers=headers)
    assert r.status_code == 200
    d = r.get_json()
    assert d["groups"] == ["group_1", "group_2"]
    assert d["users"] == ["user_1", "user_2"]
    assert d["groups_count"] == 2
    assert d["users_count"] == 2


def test_write_env_no_trailing_newline(ws):
    S, client, headers, tmp_path = ws
    env_file = tmp_path / ".env"
    env_file.write_text("KEY_A=1", encoding="utf-8")  # 末尾无换行
    S._write_env({"STAR_SCHEDULED_SEND_TIME": "08:00"})
    text = env_file.read_text(encoding="utf-8")
    assert "KEY_A=1\nSTAR_SCHEDULED_SEND_TIME=08:00" in text
    assert "KEY_A=1STAR_SCHEDULED_SEND_TIME" not in text


def test_schedule_requires_auth(ws):
    S, client, headers, _ = ws
    assert client.get("/admin/api/schedule").status_code == 401
    assert client.put("/admin/api/schedule", json={}).status_code == 401
    assert client.post("/admin/api/schedule/send", json={}).status_code == 401
    assert client.get("/admin/api/usage").status_code == 401
