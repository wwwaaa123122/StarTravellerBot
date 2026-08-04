/* ================================================================
   StarTraveller 管理后台 · 核心模块（helpers / auth / api / charts）
   ================================================================ */
"use strict";

const $  = (sel, root) => (root || document).querySelector(sel);
const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

const State = {
  token: localStorage.getItem("st_token") || "",
  user:  localStorage.getItem("st_user") || "",
  theme: localStorage.getItem("st_theme") || "dark",
  view:  "dashboard",
  charts: {},
  data: {},
};

/* ---------- 格式化 ---------- */
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}
function fmtNum(n) {
  n = Number(n) || 0;
  if (n >= 1e8) return (n / 1e8).toFixed(1) + "亿";
  if (n >= 1e4) return (n / 1e4).toFixed(1) + "万";
  return String(n);
}
function fmtBytes(n) {
  n = Number(n) || 0;
  const u = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return n.toFixed(n < 10 && i > 0 ? 1 : 0) + " " + u[i];
}
function fmtTime(ts, withSec) {
  if (!ts) return "-";
  const d = new Date(ts * 1000);
  const p = x => String(x).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}${withSec ? ":" + p(d.getSeconds()) : ""}`;
}
function fmtAgo(ts) {
  if (!ts) return "-";
  const diff = Date.now() / 1000 - ts;
  if (diff < 60) return "刚刚";
  if (diff < 3600) return Math.floor(diff / 60) + " 分钟前";
  if (diff < 86400) return Math.floor(diff / 3600) + " 小时前";
  if (diff < 86400 * 30) return Math.floor(diff / 86400) + " 天前";
  return fmtTime(ts);
}
function shortId(id) {
  return String(id || "").replace(/\s/g, "").length > 12
    ? String(id).slice(0, 6) + "…" + String(id).slice(-6)
    : String(id || "-");
}

/* ---------- Toast ---------- */
function toast(msg, type = "info") {
  const icons = {
    success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>',
    error:   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M15 9l-6 6M9 9l6 6"/></svg>',
    info:    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 8h.01M11 12h1v4h1"/></svg>',
  };
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.innerHTML = icons[type] || icons.info;
  el.appendChild(document.createTextNode(" " + msg));
  $("#toast-wrap").appendChild(el);
  setTimeout(() => { el.classList.add("out"); setTimeout(() => el.remove(), 260); }, 3200);
}

/* ---------- API ---------- */
async function api(path, opts = {}) {
  const headers = Object.assign({}, opts.headers || {});
  if (State.token) headers["Authorization"] = "Bearer " + State.token;
  if (opts.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
  const res = await fetch("/admin/api" + path, Object.assign({}, opts, { headers }));
  if (res.status === 401) { showLogin(); throw new Error("未授权"); }
  if (!res.ok) {
    let msg = "请求失败 (" + res.status + ")";
    try { msg = (await res.json()).error || msg; } catch (e) {}
    throw new Error(msg);
  }
  return res.json();
}

/* ---------- 主题 ---------- */
function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  State.theme = theme;
  localStorage.setItem("st_theme", theme);
  Object.keys(State.charts).forEach(k => State.charts[k].dispose());
  State.charts = {};
  if (State.token && State.view === "dashboard") loadDashboard();
}

/* ---------- 图表 ---------- */
const CHART_AXIS = { axisLine: { lineStyle: { color: "rgba(139,144,176,.25)" } }, axisLabel: { color: "rgba(139,144,176,.8)", fontSize: 11 } };

function chartTextColor() {
  return State.theme === "dark" ? "#eef0ff" : "#0f172a";
}
function chartGridColor() {
  return State.theme === "dark" ? "rgba(255,255,255,.08)" : "rgba(15,23,42,.10)";
}

function makeChart(id, height) {
  const el = document.getElementById(id);
  if (!el) return null;
  if (State.charts[id]) State.charts[id].dispose();
  const chart = echarts.init(el, null, { renderer: "canvas" });
  State.charts[id] = chart;
  return chart;
}

/* ---------- 时钟 ---------- */
function tickClock() {
  const el = $("#clock");
  if (!el) return;
  const d = new Date(), p = x => String(x).padStart(2, "0");
  el.textContent = `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}
setInterval(tickClock, 1000);

/* ---------- 路由 ---------- */
function navigate(view) {
  State.view = view;
  $$(".nav-item").forEach(n => n.classList.toggle("active", n.dataset.view === view));
  const titles = { dashboard: "仪表盘", users: "用户管理", memory: "记忆库", plugins: "插件管理", schedule: "定时任务", settings: "系统设置" };
  $("#page-title").textContent = titles[view] || "仪表盘";
  const viewEl = $("#view");
  viewEl.innerHTML = '<div class="skeleton" style="min-height:60vh"></div>';
  viewEl.classList.remove("view-anim");
  void viewEl.offsetWidth;
  viewEl.classList.add("view-anim");
  const loaders = { dashboard: loadDashboard, users: loadUsers, memory: loadMemory, plugins: loadPlugins, schedule: loadSchedule, settings: loadSettings };
  (loaders[view] || loadDashboard)();
}
