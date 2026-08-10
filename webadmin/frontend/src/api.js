import { store, logout } from "./store";

export async function api(path, opts = {}) {
  const headers = Object.assign({}, opts.headers || {});
  if (store.token) headers["Authorization"] = "Bearer " + store.token;
  if (opts.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
  const res = await fetch("/admin/api" + path, Object.assign({}, opts, { headers }));
  if (res.status === 401) {
    logout();
    throw new Error("登录已过期，请重新登录");
  }
  if (!res.ok) {
    let msg = "请求失败 (" + res.status + ")";
    try { msg = (await res.json()).error || msg; } catch (e) { }
    throw new Error(msg);
  }
  return res.json();
}

export async function doLogin(password) {
  const res = await fetch("/admin/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  const j = await res.json();
  if (!res.ok) throw new Error(j.message || j.error || "登录失败");
  return j.token;
}

export function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

export function fmtNum(n) {
  n = Number(n) || 0;
  if (n >= 1e8) return (n / 1e8).toFixed(1) + "亿";
  if (n >= 1e4) return (n / 1e4).toFixed(1) + "万";
  return String(n);
}

export function fmtTime(ts, withSec) {
  if (!ts) return "-";
  const d = new Date(ts * 1000);
  const p = (x) => String(x).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}${withSec ? ":" + p(d.getSeconds()) : ""}`;
}

export function fmtAgo(ts) {
  if (!ts) return "-";
  const diff = Date.now() / 1000 - ts;
  if (diff < 60) return "刚刚";
  if (diff < 3600) return Math.floor(diff / 60) + " 分钟前";
  if (diff < 86400) return Math.floor(diff / 3600) + " 小时前";
  if (diff < 86400 * 30) return Math.floor(diff / 86400) + " 天前";
  return fmtTime(ts);
}

export function shortId(id) {
  return String(id || "").replace(/\s/g, "").length > 12
    ? String(id).slice(0, 6) + "…" + String(id).slice(-6)
    : String(id || "-");
}
