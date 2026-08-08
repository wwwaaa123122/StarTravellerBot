<script setup>
import { computed, onMounted, ref } from "vue";
import * as echarts from "echarts";
import { ElMessage } from "element-plus";
import { api, fmtNum, shortId, esc } from "../../api";
import { store } from "../../store";
import StatCard from "../StatCard.vue";
import Chart from "../Chart.vue";

const ov = ref({});
const st = ref({});
const loading = ref(false);

async function load() {
  loading.value = true;
  try {
    const [o, s] = await Promise.all([api("/overview"), api("/status")]);
    ov.value = o;
    st.value = s;
  } catch (e) {
    ElMessage.error(e.message);
  } finally {
    loading.value = false;
  }
}
onMounted(load);

const stats = computed(() => ov.value.stats || {});
const sys = computed(() => st.value.status || {});
const bot = computed(() => st.value.bot || ov.value.bot || {});

const topUsers = computed(() => ov.value.top_users || []);
const statsGrid = computed(() => {
  const s = stats.value;
  const c = sys.value;
  const b = bot.value;
  return [
    { label: "机器人状态", value: b.running ? "在线运行" : "未运行", sub: "PID " + (b.pid || "-"), dot: b.running ? "success" : "off" },
    { label: "注册用户", value: fmtNum(s.users), sub: "今日签到 " + fmtNum(s.today_checked), dot: "success" },
    { label: "累计积分", value: fmtNum(s.total_points), sub: "签到系统总额", dot: "success" },
    { label: "角色数量", value: fmtNum(s.roles), sub: "角色系统", dot: "success" },
    { label: "记忆条目", value: fmtNum(s.rag_count), sub: "RAG 长期记忆", dot: "success" },
    { label: "插件数量", value: fmtNum(s.plugins), sub: "plugins/ 目录", dot: "success" },
    { label: "后台访问", value: fmtNum(s.visits), sub: "累计访问次数", dot: "success" },
    { label: "消息数量", value: fmtNum(s.total_messages), sub: "今日 " + fmtNum(s.messages_today), dot: "success" },
    { label: "AI 调用", value: fmtNum(s.total_ai_calls), sub: "今日 " + fmtNum(s.ai_calls_today), dot: "success" },
    { label: "Token 消耗", value: fmtNum(s.total_tokens), sub: "今日 " + fmtNum(s.tokens_today), dot: "success" },
    { label: "内存占用", value: (c.mem_percent || 0) + "%", sub: c.mem_used_gb + " / " + c.mem_total_gb + " GB", dot: c.mem_percent > 85 ? "off" : "success" },
    { label: "磁盘使用", value: (c.disk_percent || 0) + "%", sub: "系统磁盘", dot: c.disk_percent > 85 ? "off" : "success" },
  ];
});

const dark = () => store.theme === "dark";
const AXIS_TEXT = () => (dark() ? "#8b90b0" : "#6b7196");
const AXIS_LINE = () => (dark() ? "rgba(255,255,255,.12)" : "rgba(30,41,90,.15)");
const SPLIT = () => (dark() ? "rgba(255,255,255,.08)" : "rgba(30,41,90,.08)");
const TOOLTIP_BG = () => (dark() ? "rgba(15,20,45,.92)" : "rgba(255,255,255,.96)");
const TOOLTIP_TX = () => (dark() ? "#eef0ff" : "#1e2350");
const LABEL_TX = () => (dark() ? "#c6caf0" : "#4a5080");

const trendOption = computed(() => {
  const t = ov.value.trend || [];
  return {
    grid: { left: 8, right: 8, top: 24, bottom: 8, containLabel: true },
    tooltip: { trigger: "axis", backgroundColor: TOOLTIP_BG(), borderWidth: 0, textStyle: { color: TOOLTIP_TX() } },
    xAxis: { type: "category", data: t.map((x) => x.date), axisLabel: { color: AXIS_TEXT() }, axisLine: { lineStyle: { color: AXIS_LINE() } }, axisTick: { show: false } },
    yAxis: { type: "value", minInterval: 1, axisLabel: { color: AXIS_TEXT() }, splitLine: { lineStyle: { color: SPLIT() } } },
    series: [
      {
        name: "签到数", type: "line", smooth: true, symbol: "none",
        data: t.map((x) => x.count),
        lineStyle: { width: 3, color: "#7c6cff" },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(124,108,255,.45)" },
            { offset: 1, color: "rgba(124,108,255,0)" },
          ]),
        },
      },
    ],
  };
});

const rolesOption = computed(() => {
  const dist = ov.value.role_distribution || [];
  const palette = ["#7c6cff", "#34d399", "#fbbf24", "#38bdf8", "#fb7185", "#a78bfa", "#2dd4bf"];
  return {
    tooltip: { trigger: "item", backgroundColor: TOOLTIP_BG(), borderWidth: 0, textStyle: { color: TOOLTIP_TX() } },
    series: [
      {
        type: "pie", radius: ["58%", "80%"], center: ["50%", "52%"],
        itemStyle: { borderRadius: 8, borderColor: "transparent", borderWidth: 2 },
        label: { color: LABEL_TX(), fontSize: 12, formatter: "{b} {c}" },
        data: dist.map((d, i) => ({ name: d.name, value: d.value, itemStyle: { color: palette[i % palette.length] } })),
      },
    ],
  };
});

function avatarColor(ch) {
  const palette = ["#6366f1", "#a855f7", "#22d3ee", "#34d399", "#fbbf24", "#fb7185", "#38bdf8", "#f97316"];
  return palette[(ch || "?").charCodeAt(0) % palette.length];
}
function goUsers() {
  store.view = "users";
}
</script>

<template>
  <div class="view-dashboard">
    <div class="stats-grid">
      <StatCard
        v-for="(c, i) in statsGrid"
        :key="i"
        :label="c.label"
        :value="c.value"
        :sub="c.sub"
        :dot="c.dot"
      />
    </div>

    <div class="charts-grid">
      <div class="card chart-card">
        <div class="card-title">近 14 天签到趋势</div>
        <el-skeleton :loading="loading" animated :rows="8">
          <Chart :option="trendOption" height="280px" />
        </el-skeleton>
      </div>
      <div class="card chart-card">
        <div class="card-title">角色分布</div>
        <el-skeleton :loading="loading" animated :rows="8">
          <Chart :option="rolesOption" height="280px" />
        </el-skeleton>
      </div>
    </div>

    <div class="card panel">
      <div class="panel-head">
        <h3>活跃用户 TOP</h3>
        <el-button text type="primary" @click="goUsers">全部用户 →</el-button>
      </div>
      <el-table :data="topUsers" v-loading="loading" class="pretty-table">
        <el-table-column label="用户" min-width="180">
          <template #default="{ row }">
            <div class="user-cell">
              <div class="avatar" :style="{ background: avatarColor(row.nickname || row.user_id) }">
                {{ esc((row.nickname || row.user_id || "?").slice(0, 1)) }}
              </div>
              <div>
                <div class="user-name">{{ esc(row.nickname || shortId(row.user_id)) }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="points" label="积分" width="110">
          <template #default="{ row }">{{ fmtNum(row.points || 0) }}</template>
        </el-table-column>
        <el-table-column label="连续签到" width="110">
          <template #default="{ row }">{{ row.streak || 0 }} 天</template>
        </el-table-column>
        <el-table-column prop="affection" label="好感度" width="100">
          <template #default="{ row }">{{ row.affection || 0 }}</template>
        </el-table-column>
        <el-table-column label="最后签到" min-width="140">
          <template #default="{ row }">{{ row.last_checkin || "-" }}</template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无用户" :image-size="60" />
        </template>
      </el-table>
    </div>
  </div>
</template>
