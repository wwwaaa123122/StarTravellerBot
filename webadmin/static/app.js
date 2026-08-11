"use strict";

const TOKEN_KEY = "webadmin_token";
const $ = (sel) => document.querySelector(sel);

let state = { token: localStorage.getItem(TOKEN_KEY) || "" };


function toast(msg, isError = false) {
  const el = $("#toast");
  el.textContent = msg;
  el.classList.toggle("error", isError);
  el.classList.add("show");
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.remove("show"), 2600);
}

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers["Authorization"] = "Bearer " + state.token;
  const resp = await fetch(path, { ...options, headers });
  const data = await resp.json().catch(() => ({}));
  if (resp.status === 401) {
    if (path.endsWith("/api/login")) throw new Error(data.message || "密码错误");
    logout();
    throw new Error("登录已过期");
  }
  if (!resp.ok) throw new Error(data.message || data.error || `HTTP ${resp.status}`);
  return data;
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function fmtNum(n) { return Number(n || 0).toLocaleString(); }

function pct(n) { return (Number(n || 0) * 100).toFixed(1) + "%"; }


async function doLogin(e) {
  e.preventDefault();
  const btn = $("#login-btn");
  btn.disabled = true;
  $("#login-error").textContent = "";
  try {
    const data = await api("/admin/api/login", {
      method: "POST",
      body: JSON.stringify({ password: $("#login-password").value }),
    });
    state.token = data.token;
    localStorage.setItem(TOKEN_KEY, data.token);
    enterApp();
    toast("登录成功");
  } catch (err) {
    $("#login-error").textContent = err.message;
  } finally {
    btn.disabled = false;
  }
}

function logout() {
  state.token = "";
  localStorage.removeItem(TOKEN_KEY);
  $("#login-view").classList.remove("hidden");
  $("#app-view").classList.add("hidden");
  $("#login-password").value = "";
}

function enterApp() {
  $("#login-view").classList.add("hidden");
  $("#app-view").classList.remove("hidden");
  switchTab("overview");
  refreshBotStatus();
  setInterval(refreshBotStatus, 15000);
}


const TITLES = {
  overview: "总览", plugins: "插件管理", permissions: "权限管理",
  ai: "AI 设置", users: "用户", memory: "记忆", schedule: "定时任务", config: "配置",
};

function switchTab(name) {
  document.querySelectorAll(".nav-item[data-tab]").forEach((b) =>
    b.classList.toggle("active", b.dataset.tab === name));
  document.querySelectorAll(".tab-panel").forEach((p) => p.classList.add("hidden"));
  $("#tab-" + name).classList.remove("hidden");
  $("#page-title").textContent = TITLES[name];
  loadTab(name);
}

async function loadTab(name) {
  try {
    if (name === "overview") await renderOverview();
    else if (name === "plugins") await renderPlugins();
    else if (name === "permissions") await renderPermissions();
    else if (name === "ai") await renderAi();
    else if (name === "users") await renderUsers();
    else if (name === "memory") await renderMemory();
    else if (name === "schedule") await renderSchedule();
    else if (name === "config") await renderConfig();
  } catch (err) {
    $("#tab-" + name).innerHTML = `<div class="empty">加载失败：${esc(err.message)}</div>`;
  }
}


async function renderOverview() {
  const d = await api("/admin/api/overview");
  const s = d.stats, ai = d.ai_stats || {};
  const maxTrend = Math.max(1, ...d.trend.map((t) => t.count));
  const bars = d.trend.map((t) =>
    `<div class="bar-col"><div class="bar" style="height:${Math.round((t.count / maxTrend) * 80)}px"></div>
     <span class="bar-count">${t.count}</span><span class="bar-label">${t.date.slice(5)}</span></div>`).join("");

  $("#tab-overview").innerHTML = `
    <div class="cards">
      ${card("👥 用户", s.users, "今日签到 " + s.today_checked)}
      ${card("💬 消息", s.total_messages, "今日 " + s.messages_today)}
      ${card("🤖 AI 调用", s.total_ai_calls, "今日 " + s.ai_calls_today)}
      ${card("🔤 Token", fmtNum(s.total_tokens), "今日 " + fmtNum(s.tokens_today))}
      ${card("🔌 插件", s.plugins)}
      ${card("⭐ 积分", fmtNum(s.total_points))}
      ${card("🧠 RAG 记录", s.rag_count)}
      ${card("👀 访问", s.visits)}
    </div>
    <div class="section-title">近 14 天签到趋势</div>
    <div class="table-wrap"><div class="bars">${bars}</div></div>
    <div class="section-title">AI 调用统计（今日）</div>
    <div class="cards">
      ${card("📨 请求数", ai.requests)}
      ${card("🔤 Token", fmtNum(ai.total_tokens))}
      ${card("⏱ 平均延迟", (ai.avg_latency || 0) + "s")}
      ${card("⚠️ 错误率", pct(ai.error_rate))}
      ${card("💰 预估费用", "¥" + (ai.cost || 0))}
    </div>
    <div class="section-title">角色分布</div>
    <div class="table-wrap"><table><tr><th>角色</th><th>人数</th></tr>
      ${(d.role_distribution || []).map((r) => `<tr><td>${esc(r.name)}</td><td>${r.value}</td></tr>`).join("") || '<tr><td colspan="2" class="empty">暂无数据</td></tr>'}
    </table></div>`;
}

function card(label, value, sub = "") {
  return `<div class="card"><div class="label">${label}</div><div class="value">${value}</div>
    ${sub ? `<div class="sub">${sub}</div>` : ""}</div>`;
}


async function renderPlugins() {
  const d = await api("/admin/api/plugins/toggle");
  const rows = d.plugins.map((p) => `
    <tr>
      <td><strong>${esc(p.name)}</strong></td>
      <td>${esc(p.keyword || "—")}</td>
      <td>${esc(p.help || "—")}</td>
      <td>${p.enabled ? '<span class="tag green">启用</span>' : '<span class="tag red">禁用</span>'}</td>
      <td><label class="switch"><input type="checkbox" ${p.enabled ? "checked" : ""}
        onchange="togglePlugin('${esc(p.name)}', this.checked)"><span class="slider"></span></label></td>
    </tr>`).join("");

  $("#tab-plugins").innerHTML = `
    <div class="table-wrap"><table><tr><th>名称</th><th>关键字</th><th>帮助</th><th>状态</th><th>开关</th></tr>
    ${rows || '<tr><td colspan="5" class="empty">未发现插件</td></tr>'}</table></div>
    <div class="section-title">说明</div>
    <div class="card" style="color:var(--muted)">切换开关后写入 data/reload.flag，机器人进程约 10 秒内热重载生效（无需重启）。</div>`;
}

async function togglePlugin(name, enabled) {
  try {
    await api("/admin/api/plugins/toggle", {
      method: "PUT",
      body: JSON.stringify({ [name]: enabled }),
    });
    toast(enabled ? `已启用 ${name}（等待热重载）` : `已禁用 ${name}（等待热重载）`);
  } catch (err) {
    toast(err.message, true);
    renderPlugins();
  }
}


async function renderPermissions() {
  const d = await api("/admin/api/permissions");
  $("#tab-permissions").innerHTML = `
    <div class="form-grid">
      <div class="field">
        <label>管理员（ROOT_User，逗号分隔 OpenID）</label>
        <input id="perm-root" value="${esc(d.root_users.join(", "))}">
      </div>
      <div class="field">
        <label>黑名单（black_list，逗号分隔 OpenID，消息被静默忽略）</label>
        <input id="perm-black" value="${esc(d.blacklist.join(", "))}">
      </div>
    </div>
    <div style="margin-top:16px">
      <label class="switch" title="允许 AI 对话">
        <input type="checkbox" id="perm-ai" ${d.allow_ai ? "checked" : ""}><span class="slider"></span>
      </label>
      <span style="margin-left:10px">允许 AI 对话</span>
    </div>
    <div style="margin-top:20px"><button class="btn" onclick="savePermissions()">保存权限</button></div>`;
}

async function savePermissions() {
  try {
    await api("/admin/api/permissions", {
      method: "PUT",
      body: JSON.stringify({
        root_users: $("#perm-root").value.split(",").map((s) => s.trim()).filter(Boolean),
        blacklist: $("#perm-black").value.split(",").map((s) => s.trim()).filter(Boolean),
        allow_ai: $("#perm-ai").checked,
      }),
    });
    toast("权限已保存");
  } catch (err) {
    toast(err.message, true);
  }
}


async function renderAi() {
  const d = await api("/admin/api/ai-settings");
  const mode = d.enable_network === "GoogleGemini" ? "GoogleGemini" : "Ds";
  $("#tab-ai").innerHTML = `
    <div class="form-grid">
      <div class="field"><label>模型提供商</label>
        <select id="ai-mode">
          <option value="Ds" ${mode === "Ds" ? "selected" : ""}>DeepSeek / OpenAI 兼容</option>
          <option value="GoogleGemini" ${mode === "GoogleGemini" ? "selected" : ""}>Google Gemini</option>
        </select></div>
      <div class="field"><label>模型名称</label>
        <input id="ai-model" value="${esc(d.ai_model)}"></div>
      <div class="field"><label>Base URL（OpenAI 兼容服务）</label>
        <input id="ai-base" value="${esc(d.ai_base_url)}"></div>
      <div class="field"><label>Max Tokens</label>
        <input id="ai-max" type="number" value="${esc(d.ai_max_tokens)}"></div>
      <div class="field"><label>Temperature</label>
        <input id="ai-temp" type="number" step="0.1" value="${esc(d.ai_temperature)}"></div>
      <div class="field"><label>DeepSeek Key（已掩码，留空不修改）</label>
        <input id="ai-ds" value="${esc(d.deepseek_key)}"></div>
      <div class="field"><label>Gemini Key（已掩码，留空不修改）</label>
        <input id="ai-gemini" value="${esc(d.gemini_key)}"></div>
      <div class="field"><label>OpenAI Key（已掩码，留空不修改）</label>
        <input id="ai-openai" value="${esc(d.openai_key)}"></div>
    </div>
    <div style="margin-top:20px"><button class="btn" onclick="saveAi()">保存 AI 设置</button></div>`;
}

async function saveAi() {
  try {
    const body = {
      EnableNetwork: $("#ai-mode").value,
      ai_model: $("#ai-model").value.trim(),
      ai_base_url: $("#ai-base").value.trim(),
      ai_max_tokens: Number($("#ai-max").value),
      ai_temperature: Number($("#ai-temp").value),
    };
    for (const [id, key] of [["ai-ds", "deepseek_key"], ["ai-gemini", "gemini_key"], ["ai-openai", "openai_key"]]) {
      const v = $("#" + id).value.trim();
      if (v && !v.includes("***")) body[key] = v;
    }
    await api("/admin/api/ai-settings", { method: "PUT", body: JSON.stringify(body) });
    toast("AI 设置已保存");
    renderAi();
  } catch (err) {
    toast(err.message, true);
  }
}


async function renderUsers() {
  const d = await api("/admin/api/users");
  const rows = d.users.map((u) => `
    <tr>
      <td>${esc(u.nickname || "—")}</td>
      <td>${esc(u.user_id)}</td>
      <td>${u.points}</td>
      <td>${u.affection}</td>
      <td>${u.streak}</td>
      <td>${esc(u.last_checkin || "—")}</td>
      <td><span class="tag gray">${esc(u.role || "默认")}</span></td>
    </tr>`).join("");
  $("#tab-users").innerHTML = `
    <div class="table-wrap"><table><tr><th>昵称</th><th>OpenID</th><th>积分</th><th>好感度</th><th>连续天数</th><th>最近签到</th><th>角色</th></tr>
    ${rows || '<tr><td colspan="7" class="empty">暂无签到用户</td></tr>'}</table></div>`;
}


async function renderMemory() {
  const d = await api("/admin/api/memory");
  const rows = d.records.map((r) => `
    <tr>
      <td>${esc(r.user_id)}</td>
      <td style="white-space:normal;max-width:420px">${esc((r.question || "").slice(0, 60))}</td>
      <td style="white-space:normal;max-width:420px">${esc((r.answer || "").slice(0, 60))}</td>
      <td>${esc(r.time || "—")}</td>
    </tr>`).join("");
  $("#tab-memory").innerHTML = `
    <div class="section-title">RAG 记忆（最近 ${d.records.length} 条，共 ${d.users.length} 个用户）</div>
    <div class="table-wrap"><table><tr><th>用户</th><th>问题</th><th>回答</th><th>时间</th></tr>
    ${rows || '<tr><td colspan="4" class="empty">暂无记忆</td></tr>'}</table></div>`;
}


async function renderSchedule() {
  const d = await api("/admin/api/schedule");
  $("#tab-schedule").innerHTML = `
    <div class="cards">
      ${card("⏰ 定时发送", d.send_time)}
      ${card("📡 状态", d.enabled ? "启用" : "禁用", d.today_done ? "今日已发送" : "今日未发送")}
      ${card("🕒 上次发送", esc(d.last_sent || "从未"))}
      ${card("📢 通知群数", d.channels.length)}
    </div>
    <div class="section-title">群发内容</div>
    <div class="table-wrap"><div style="padding:14px;white-space:pre-wrap;color:var(--muted)">${esc(d.content || "（未配置）")}</div></div>`;
}


async function renderConfig() {
  const d = await api("/admin/api/config");
  $("#tab-config").innerHTML = `
    <div class="cards">
      ${card("🤖 机器人", esc(d.bot_info.name || "—"))}
      ${card("🛠 日志级别", esc(d.bot_info.log_level || "—"))}
      ${card("📄 配置路径", esc(d.bot_info.config_path || "—"), "v" + d.version)}
    </div>
    <div class="section-title">config.json（敏感字段已掩码）</div>
    <div class="table-wrap"><pre style="padding:14px;overflow-x:auto;font-size:12px;color:var(--muted)">${esc(JSON.stringify(d.config, null, 2))}</pre></div>`;
}


async function refreshBotStatus() {
  try {
    const d = await api("/admin/api/ping");
    const el = $("#bot-status");
    el.className = "bot-status online";
    el.innerHTML = `<span class="dot"></span> ${esc(d.name)} v${d.version}`;
    $("#topbar-info").textContent = "";
  } catch (err) {
    const el = $("#bot-status");
    el.className = "bot-status offline";
    el.innerHTML = `<span class="dot"></span> 服务离线`;
  }
}


document.addEventListener("DOMContentLoaded", () => {
  $("#login-form").addEventListener("submit", doLogin);
  $("#logout-btn").addEventListener("click", logout);
  document.querySelectorAll(".nav-item[data-tab]").forEach((b) =>
    b.addEventListener("click", () => switchTab(b.dataset.tab)));
  if (state.token) {
    enterApp();
  } else {
    $("#login-view").classList.remove("hidden");
  }
});
