/* ================================================================
   StarTraveller 管理后台 · 视图模块（对齐 server.py 实际 API）
   ================================================================ */
"use strict";

/* ---------- 登录 / 登出 ---------- */
function showLogin() {
  State.token = "";
  localStorage.removeItem("st_token");
  localStorage.removeItem("st_user");
  $("#app").classList.add("hidden");
  $("#login-view").classList.remove("hidden");
  $("#login-password").value = "";
  const btn = $("#login-btn");
  if (btn) { btn.disabled = false; btn.textContent = "登 录"; }
  setTimeout(() => { const i = $("#login-password"); if (i) i.focus(); }, 50);
}
function showShell() {
  $("#login-view").classList.add("hidden");
  $("#app").classList.remove("hidden");
}

async function doLogin(pwd) {
  const btn = $("#login-btn");
  btn.disabled = true;
  btn.textContent = "验证中…";
  try {
    const r = await fetch("/admin/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: pwd }),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.message || j.error || "登录失败");
    State.token = j.token;
    State.user = "admin";
    localStorage.setItem("st_token", j.token);
    localStorage.setItem("st_user", State.user);
    toast("欢迎回来，" + State.user, "success");
    showShell();
    navigate(State.view);
  } catch (e) {
    toast(e.message, "error");
    btn.disabled = false;
    btn.textContent = "登 录";
  }
}

/* ---------- 仪表盘 ---------- */
function statCard(label, value, sub, accent) {
  return `<div class="stat-card glass">
    <div class="stat-label">${esc(label)}</div>
    <div class="stat-value ${accent ? "accent-" + accent : ""}">${value}</div>
    <div class="stat-sub">${esc(sub || "")}</div>
  </div>`;
}

async function loadDashboard() {
  const view = $("#view");
  try {
    const [ov, st] = await Promise.all([api("/overview"), api("/status")]);
    State.data.overview = ov; State.data.status = st;
    const s = ov.stats || {};
    const sys = st.status || {};
    const bot = st.bot || ov.bot || {};
    view.innerHTML = `
      <div class="stats-grid">
        ${statCard("机器人状态", bot.running ? "在线运行" : "未运行", "PID " + (bot.pid || "-"), bot.running ? "ok" : "bad")}
        ${statCard("注册用户", fmtNum(s.users), "今日签到 " + fmtNum(s.today_checked), "ok")}
        ${statCard("累计积分", fmtNum(s.total_points), "签到系统总额", "ok")}
        ${statCard("角色数量", fmtNum(s.roles), "角色系统", "ok")}
        ${statCard("记忆条目", fmtNum(s.rag_count), "RAG 长期记忆", "ok")}
        ${statCard("插件数量", fmtNum(s.plugins), "plugins/ 目录", "ok")}
        ${statCard("后台访问", fmtNum(s.visits), "累计访问次数", "ok")}
        ${statCard("CPU 使用率", (sys.cpu_percent || 0) + "%", sys.cpu_count + " 核", sys.cpu_percent > 80 ? "bad" : "ok")}
        ${statCard("内存占用", (sys.mem_percent || 0) + "%", sys.mem_used_gb + " / " + sys.mem_total_gb + " GB", sys.mem_percent > 85 ? "bad" : "ok")}
        ${statCard("磁盘使用", (sys.disk_percent || 0) + "%", "系统磁盘", sys.disk_percent > 85 ? "bad" : "ok")}
      </div>
      <div class="charts-grid">
        <div class="chart-card glass"><h3>近 14 天签到趋势</h3><div id="ch-trend" class="chart"></div></div>
        <div class="chart-card glass"><h3>角色分布</h3><div id="ch-roles" class="chart"></div></div>
      </div>
      <div class="glass panel">
        <div class="panel-head"><h3>活跃用户 TOP</h3><button class="btn btn-ghost" onclick="navigate('users')">全部用户 →</button></div>
        <div class="table-wrap">
        <table class="table">
          <thead><tr><th>用户</th><th>积分</th><th>连续签到</th><th>好感度</th><th>最后签到</th></tr></thead>
          <tbody>
            ${(ov.top_users || []).map(u => {
              const name = u.nickname || shortId(u.user_id);
              const ch = (u.nickname || u.user_id || "?").slice(0, 1);
              return `
              <tr>
                <td><div class="user-cell">
                  <div class="avatar">${esc(ch)}</div>
                  <div><div class="user-name">${esc(name)}</div></div>
                </div></td>
                <td>${fmtNum(u.points || 0)}</td>
                <td>${u.streak || 0} 天</td>
                <td>${u.affection || 0}</td>
                <td>${u.last_checkin || "-"}</td>
              </tr>`;
            }).join("") || `<tr><td colspan="5" class="td-empty">暂无用户</td></tr>`}
          </tbody>
        </table>
        </div>
      </div>`;
    renderTrendChart(ov.trend);
    renderRolesChart(ov.role_distribution);
  } catch (e) {
    view.innerHTML = `<div class="empty glass"><h3>加载失败</h3><p>${esc(e.message)}</p></div>`;
  }
}

function renderTrendChart(trend) {
  const chart = makeChart("ch-trend");
  if (!chart) return;
  chart.setOption({
    grid: { left: 8, right: 8, top: 24, bottom: 8, containLabel: true },
    tooltip: { trigger: "axis", backgroundColor: "rgba(15,20,45,.92)", borderWidth: 0, textStyle: { color: "#eef0ff" } },
    xAxis: Object.assign({ type: "category", data: trend.map(t => t.date) }, CHART_AXIS),
    yAxis: Object.assign({ type: "value", minInterval: 1, splitLine: { lineStyle: { color: chartGridColor() } } }, CHART_AXIS),
    series: [{
      name: "签到数", type: "line", smooth: true, symbol: "none",
      data: trend.map(t => t.count),
      lineStyle: { width: 3, color: "#7c6cff" },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: "rgba(124,108,255,.45)" },
        { offset: 1, color: "rgba(124,108,255,0)" },
      ]) },
    }],
  });
}

function renderRolesChart(dist) {
  const chart = makeChart("ch-roles");
  if (!chart) return;
  const palette = ["#7c6cff", "#34d399", "#fbbf24", "#38bdf8", "#fb7185", "#a78bfa", "#2dd4bf"];
  chart.setOption({
    tooltip: { trigger: "item", backgroundColor: "rgba(15,20,45,.92)", borderWidth: 0, textStyle: { color: "#eef0ff" } },
    series: [{
      type: "pie", radius: ["58%", "80%"], center: ["50%", "52%"],
      itemStyle: { borderRadius: 8, borderColor: "transparent", borderWidth: 2 },
      label: { color: chartTextColor(), fontSize: 12, formatter: "{b} {c}" },
      data: (dist || []).map((d, i) => ({ name: d.name, value: d.value, itemStyle: { color: palette[i % palette.length] } })),
    }],
  });
}

/* ---------- 用户管理 ---------- */
async function loadUsers() {
  const view = $("#view");
  try {
    const res = await api("/users");
    const users = (res.users || []).slice().sort((a, b) => (b.points || 0) - (a.points || 0));
    const maxP = Math.max(1, ...users.map(u => u.points || 0));
    view.innerHTML = `
      <div class="stats-grid small">
        ${statCard("用户总数", fmtNum(users.length), "签到用户", "ok")}
        ${statCard("总积分", fmtNum(users.reduce((a, u) => a + (u.points || 0), 0)), "累计发放", "ok")}
      </div>
      <div class="glass panel">
        <div class="panel-head"><h3>签到用户（${users.length}）</h3></div>
        <div class="table-wrap">
        <table class="table">
          <thead><tr><th>用户</th><th>角色</th><th>积分</th><th>好感度</th><th>连续天数</th><th>最后签到</th><th>积分占比</th></tr></thead>
          <tbody>
            ${users.map(u => {
              const name = u.nickname || shortId(u.user_id);
              const ch = (u.nickname || u.user_id || "?").slice(0, 1);
              return `
              <tr>
                <td><div class="user-cell">
                  <div class="avatar">${esc(ch)}</div>
                  <div><div class="user-name">${esc(name)}</div></div>
                </div></td>
                <td>${esc(u.role || "默认")}</td>
                <td>${fmtNum(u.points || 0)}</td>
                <td>${u.affection || 0}</td>
                <td>${u.streak || 0} 天</td>
                <td>${u.last_checkin || "-"}</td>
                <td><div class="progress"><i style="width:${Math.round(((u.points || 0) / maxP) * 100)}%"></i></div></td>
              </tr>`;
            }).join("") || `<tr><td colspan="7" class="td-empty">暂无签到用户</td></tr>`}
          </tbody>
        </table>
        </div>
      </div>`;
  } catch (e) {
    view.innerHTML = `<div class="empty glass"><h3>加载失败</h3><p>${esc(e.message)}</p></div>`;
  }
}

/* ---------- 记忆库 ---------- */
async function loadMemory() {
  const view = $("#view");
  try {
    const mem = await api("/memory");
    const recs = mem.records || [];
    view.innerHTML = `
      <div class="stats-grid small">
        ${statCard("记忆总数", fmtNum(recs.length), "RAG 长期记忆", "ok")}
        ${statCard("关联用户", fmtNum(Array.isArray(mem.users) ? mem.users.length : mem.users), "独立用户", "ok")}
      </div>
      <div class="glass panel">
        <div class="panel-head"><h3>全部记忆</h3><span class="hint">最近更新在前</span></div>
        <div class="mem-list">
          ${recs.map(r => `
            <div class="mem-item">
              <div class="mem-q">${esc(r.question || "")}</div>
              <div class="mem-a">${esc(r.answer || "")}</div>
              <div class="mem-meta">
                <span class="badge badge-src">${shortId(r.user_id)}</span>
                <span>${fmtTime(r.ts, true)}</span>
              </div>
            </div>`).join("") || `<div class="td-empty">暂无记忆</div>`}
        </div>
      </div>`;
  } catch (e) {
    view.innerHTML = `<div class="empty glass"><h3>加载失败</h3><p>${esc(e.message)}</p></div>`;
  }
}

/* ---------- 插件管理 ---------- */
async function loadPlugins() {
  const view = $("#view");
  try {
    const pl = await api("/plugins");
    const list = pl.plugins || [];
    view.innerHTML = `
      <div class="stats-grid small">
        ${statCard("插件总数", list.length, "plugins/ 目录", "ok")}
        ${statCard("已解析", list.filter(p => p.keyword || p.help).length, "含关键字/帮助", "ok")}
      </div>
      <div class="plugins-grid">
        ${list.map(p => `
          <div class="plugin-card glass">
            <div class="plugin-top">
              <span class="dot dot-ok"></span>
              <span class="plugin-name">${esc(p.file.replace(/\.py$/, ""))}</span>
              <span class="plugin-trigger">${esc(p.keyword || "无关键字")}</span>
            </div>
            <p class="plugin-desc">${esc(p.help || "无帮助描述")}</p>
            <div class="plugin-meta"><span class="mono">${esc(p.file)}</span></div>
          </div>`).join("") || `<div class="td-empty">plugins/ 目录为空</div>`}
      </div>`;
  } catch (e) {
    view.innerHTML = `<div class="empty glass"><h3>加载失败</h3><p>${esc(e.message)}</p></div>`;
  }
}

/* ---------- 定时任务 ---------- */
async function loadSchedule() {
  const view = $("#view");
  try {
    const sc = await api("/schedule");
    view.innerHTML = `
      <div class="stats-grid small">
        ${statCard("任务状态", sc.enabled ? "已启用" : "已停用", "scheduled_send 配置", sc.enabled ? "ok" : "warn")}
        ${statCard("发送时间", sc.send_time || "-", "每日定时", "ok")}
        ${statCard("今日状态", sc.today_done ? "已发送" : "待发送", "上次发送 " + (sc.last_sent || "-"), sc.today_done ? "ok" : "warn")}
        ${statCard("目标频道", fmtNum((sc.channels || []).length), "channel id", "ok")}
      </div>
      <div class="glass panel">
        <div class="panel-head"><h3>定时发送配置</h3></div>
        <div class="detail-grid">
          <div class="detail-item"><span class="detail-key">enabled</span><span class="detail-val">${sc.enabled ? "true" : "false"}</span></div>
          <div class="detail-item"><span class="detail-key">send_time</span><span class="detail-val mono">${esc(sc.send_time || "-")}</span></div>
          <div class="detail-item"><span class="detail-key">last_sent</span><span class="detail-val mono">${esc(sc.last_sent || "-")}</span></div>
          <div class="detail-item"><span class="detail-key">today_done</span><span class="detail-val">${sc.today_done ? "true" : "false"}</span></div>
        </div>
        <div class="detail-grid">
          <div class="detail-item full"><span class="detail-key">发送内容</span><span class="detail-val">${esc(sc.content || "-")}</span></div>
        </div>
        <div class="detail-grid">
          <div class="detail-item full"><span class="detail-key">目标频道</span>
            <span class="detail-val">${(sc.channels || []).map(c => `<span class="badge badge-src mono">${esc(c)}</span>`).join(" ") || "-"}</span>
          </div>
        </div>
      </div>`;
  } catch (e) {
    view.innerHTML = `<div class="empty glass"><h3>加载失败</h3><p>${esc(e.message)}</p></div>`;
  }
}

/* ---------- 系统设置 ---------- */
async function loadSettings() {
  const view = $("#view");
  try {
    const [cfg, st] = await Promise.all([api("/config"), api("/status")]);
    const bi = cfg.bot_info || {};
    const sys = st.status || {};
    const bot = st.bot || {};
    view.innerHTML = `
      <div class="stats-grid small">
        ${statCard("机器人名称", bi.name || "-", "来自 config.json", "ok")}
        ${statCard("运行状态", bot.running ? "运行中" : "未运行", "PID " + (bot.pid || "-"), bot.running ? "ok" : "warn")}
        ${statCard("沙箱模式", bi.sandbox ? "是" : "否", "is_sandbox", "ok")}
      </div>
      <div class="glass panel">
        <div class="panel-head"><h3>机器人信息</h3><span class="hint">敏感字段已脱敏</span></div>
        <div class="detail-grid">
          <div class="detail-item"><span class="detail-key">bot_name</span><span class="detail-val">${esc(bi.name || "-")}</span></div>
          <div class="detail-item"><span class="detail-key">log_level</span><span class="detail-val mono">${esc(bi.log_level || "-")}</span></div>
          <div class="detail-item"><span class="detail-key">sandbox</span><span class="detail-val">${bi.sandbox === undefined ? "-" : bi.sandbox ? "true" : "false"}</span></div>
          <div class="detail-item"><span class="detail-key">appid</span><span class="detail-val mono">${esc(bi.openqq_appid || "-")}</span></div>
          <div class="detail-item"><span class="detail-key">config_path</span><span class="detail-val mono">${esc(bi.config_path || "-")}</span></div>
          <div class="detail-item"><span class="detail-key">后端版本</span><span class="detail-val mono">${esc(cfg.version || "-")}</span></div>
        </div>
      </div>
      <div class="glass panel">
        <div class="panel-head"><h3>运行配置（脱敏）</h3></div>
        <div class="detail-grid">
          ${Object.entries(cfg.config || {}).map(([k, v]) => `
            <div class="detail-item">
              <span class="detail-key">${esc(k)}</span>
              <span class="detail-val mono">${esc(typeof v === "object" ? JSON.stringify(v) : v)}</span>
            </div>`).join("") || `<div class="td-empty">config.json 为空或未找到</div>`}
        </div>
      </div>
      <div class="glass panel">
        <div class="panel-head"><h3>系统环境</h3></div>
        <div class="detail-grid">
          <div class="detail-item"><span class="detail-key">uptime</span><span class="detail-val">${esc(sys.uptime_text || "-")}</span></div>
          <div class="detail-item"><span class="detail-key">python</span><span class="detail-val mono">${esc(sys.python || "-")}</span></div>
          <div class="detail-item"><span class="detail-key">platform</span><span class="detail-val mono">${esc(sys.platform || "-")}</span></div>
          <div class="detail-item"><span class="detail-key">webadmin_mem</span><span class="detail-val mono">${sys.webadmin_mem_mb || 0} MB</span></div>
        </div>
      </div>`;
  } catch (e) {
    view.innerHTML = `<div class="empty glass"><h3>加载失败</h3><p>${esc(e.message)}</p></div>`;
  }
}

/* ---------- 启动 ---------- */
function boot() {
  applyTheme(State.theme);
  $("#login-form").addEventListener("submit", e => {
    e.preventDefault();
    doLogin($("#login-password").value.trim());
  });
  $("#logout-btn").addEventListener("click", () => { toast("已退出登录"); showLogin(); });
  $("#refresh-btn").addEventListener("click", () => navigate(State.view));
  $("#theme-toggle").addEventListener("click", () => applyTheme(State.theme === "dark" ? "light" : "dark"));

  const isMobile = () => window.matchMedia("(max-width: 820px)").matches;
  const closeSidebar = () => {
    const app = $(".app");
    app.classList.remove("menu-open");
    document.body.classList.remove("sidebar-lock");
  };
  const openSidebar = () => {
    const app = $(".app");
    app.classList.add("menu-open");
    document.body.classList.add("sidebar-lock");
  };

  // 侧栏收起/抽屉开关：桌面端切换图标栏，手机端切换抽屉
  $("#sidebar-toggle").addEventListener("click", () => {
    const app = $(".app");
    if (isMobile()) {
      app.classList.contains("menu-open") ? closeSidebar() : openSidebar();
    } else {
      app.classList.toggle("collapsed");
      localStorage.setItem("st_sidebar_collapsed", app.classList.contains("collapsed") ? "1" : "0");
    }
  });

  // 恢复桌面端收起偏好
  if (!isMobile() && localStorage.getItem("st_sidebar_collapsed") === "1") {
    $(".app").classList.add("collapsed");
  }

  // 手机端：点击遮罩关闭抽屉
  $("#sidebar-mask").addEventListener("click", closeSidebar);

  // 导航：手机端点击后自动收起抽屉
  $$(".nav-item").forEach(n => n.addEventListener("click", () => {
    navigate(n.dataset.view);
    if (isMobile()) closeSidebar();
  }));

  tickClock();
  if (State.token) { showShell(); applyTheme(State.theme); navigate(State.view); } else { showLogin(); }
}
document.addEventListener("DOMContentLoaded", boot);
