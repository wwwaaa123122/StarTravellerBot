<script setup>
import { computed, onMounted, ref } from "vue";
import { api, fmtNum, shortId, esc } from "../../api";
import { store } from "../../store";
import { toast } from "../../ui/toast";
import StatCard from "../StatCard.vue";
import LineChart from "../charts/LineChart.vue";
import DonutChart from "../charts/DonutChart.vue";
import UiTable from "../ui/UiTable.vue";
import UiSkeleton from "../ui/UiSkeleton.vue";
import UiButton from "../ui/UiButton.vue";

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
    toast.error(e.message);
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
    { label: "机器人状态", value: b.running ? "在线" : "离线", sub: "PID " + (b.pid || "-"), dot: b.running ? "success" : "off" },
    { label: "注册用户", value: fmtNum(s.users), sub: "今日签到 " + fmtNum(s.today_checked), dot: "success" },
    { label: "累计积分", value: fmtNum(s.total_points), sub: "签到系统", dot: "success" },
    { label: "角色数量", value: fmtNum(s.roles), sub: "角色系统", dot: "success" },
    { label: "记忆条目", value: fmtNum(s.rag_count), sub: "RAG 长期记忆", dot: "success" },
    { label: "插件数量", value: fmtNum(s.plugins), sub: "plugins/ 目录", dot: "success" },
    { label: "后台访问", value: fmtNum(s.visits), sub: "累计访问", dot: "success" },
    { label: "消息数量", value: fmtNum(s.total_messages), sub: "今日 " + fmtNum(s.messages_today), dot: "success" },
    { label: "AI 调用", value: fmtNum(s.total_ai_calls), sub: "今日 " + fmtNum(s.ai_calls_today), dot: "success" },
    { label: "Token 消耗", value: fmtNum(s.total_tokens), sub: "今日 " + fmtNum(s.tokens_today), dot: "success" },
    { label: "内存占用", value: (c.mem_percent || 0) + "%", sub: c.mem_used_gb + " / " + c.mem_total_gb + " GB", dot: c.mem_percent > 85 ? "off" : "success" },
    { label: "磁盘使用", value: (c.disk_percent || 0) + "%", sub: "系统磁盘", dot: c.disk_percent > 85 ? "off" : "success" },
  ];
});

const trendData = computed(() =>
  (ov.value.trend || []).map((x) => ({ label: x.date, value: x.count }))
);

const roleData = computed(() => ov.value.role_distribution || []);

const userColumns = [
  { key: "user", label: "用户", width: "32%" },
  { key: "points", label: "积分", width: 90, sortable: true },
  { key: "streak", label: "连续签到", width: 100, sortable: true },
  { key: "affection", label: "好感度", width: 90, sortable: true },
  { key: "last_checkin", label: "最后签到" },
];

function avatarColor(ch) {
  const palette = ["#2a3a55", "#c0392b", "#4e8a6c", "#d9912f", "#3d5a80", "#8c6e9e", "#d98c8c", "#6e8b74"];
  return palette[(ch || "?").charCodeAt(0) % palette.length];
}

function goUsers() {
  store.view = "users";
}
</script>

<template>
  <div class="view-dashboard">
    <div class="stats-grid">
      <StatCard v-for="(c, i) in statsGrid" :key="i" :label="c.label" :value="c.value" :sub="c.sub" :dot="c.dot" />
    </div>

    <div class="charts-grid">
      <div class="card chart-card">
        <h3 class="card-title">近 14 天签到趋势</h3>
        <UiSkeleton v-if="loading" :rows="6" />
        <LineChart v-else :data="trendData" height="272" />
      </div>
      <div class="card chart-card">
        <h3 class="card-title">角色分布</h3>
        <UiSkeleton v-if="loading" :rows="6" />
        <DonutChart v-else :data="roleData" height="272" />
      </div>
    </div>

    <div class="card panel">
      <div class="panel-head">
        <h3>活跃用户 TOP</h3>
        <div class="spacer"></div>
        <UiButton variant="text" size="sm" @click="goUsers">全部用户 →</UiButton>
      </div>
      <UiSkeleton v-if="loading" :rows="5" />
      <UiTable v-else :columns="userColumns" :data="topUsers" empty-text="暂无用户">
        <template #cell-user="{ row }">
          <div class="user-cell">
            <div class="avatar" :style="{ background: avatarColor(row.nickname || row.user_id) }">
              {{ esc((row.nickname || row.user_id || "?").slice(0, 1)) }}
            </div>
            <div>
              <div class="user-name">{{ esc(row.nickname || shortId(row.user_id)) }}</div>
            </div>
          </div>
        </template>
        <template #cell-points="{ row }"><span class="num">{{ fmtNum(row.points || 0) }}</span></template>
        <template #cell-streak="{ row }"><span class="num">{{ row.streak || 0 }} 天</span></template>
        <template #cell-affection="{ row }"><span class="num">{{ row.affection || 0 }}</span></template>
        <template #cell-last_checkin="{ row }">{{ row.last_checkin || "-" }}</template>
      </UiTable>
    </div>
  </div>
</template>

<style scoped>
.charts-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; margin-bottom: 20px; }
.spacer { flex: 1; }
@media (max-width: 1100px) {
  .charts-grid { grid-template-columns: 1fr; }
}
</style>