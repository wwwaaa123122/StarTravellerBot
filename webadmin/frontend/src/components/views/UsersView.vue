<script setup>
import { computed, onMounted, ref } from "vue";
import { api, fmtNum, shortId, esc } from "../../api";
import { toast } from "../../ui/toast";
import StatCard from "../StatCard.vue";
import UiTable from "../ui/UiTable.vue";
import UiSkeleton from "../ui/UiSkeleton.vue";
import UiTag from "../ui/UiTag.vue";

const users = ref([]);
const loading = ref(false);

async function load() {
  loading.value = true;
  try {
    const res = await api("/users");
    users.value = (res.users || []).slice().sort((a, b) => (b.points || 0) - (a.points || 0));
  } catch (e) {
    toast.error(e.message);
  } finally {
    loading.value = false;
  }
}
onMounted(load);

const maxP = computed(() => Math.max(1, ...users.value.map((u) => u.points || 0)));
const totalPoints = computed(() => users.value.reduce((a, u) => a + (u.points || 0), 0));

const cards = computed(() => [
  { label: "用户总数", value: fmtNum(users.value.length), sub: "签到用户", dot: "success" },
  { label: "总积分", value: fmtNum(totalPoints.value), sub: "累计发放", dot: "success" },
]);

const columns = [
  { key: "user", label: "用户", width: "26%" },
  { key: "role", label: "角色", width: 100 },
  { key: "points", label: "积分", width: 100, sortable: true },
  { key: "affection", label: "好感度", width: 90, sortable: true },
  { key: "streak", label: "连续天数", width: 100, sortable: true },
  { key: "last_checkin", label: "最后签到", width: 130 },
  { key: "share", label: "积分占比" },
];

function avatarColor(ch) {
  const palette = ["#2a3a55", "#c0392b", "#4e8a6c", "#d9912f", "#3d5a80", "#8c6e9e", "#d98c8c", "#6e8b74"];
  return palette[(ch || "?").charCodeAt(0) % palette.length];
}
</script>

<template>
  <div class="view-users">
    <div class="stats-grid small">
      <StatCard v-for="(c, i) in cards" :key="i" :label="c.label" :value="c.value" :sub="c.sub" :dot="c.dot" />
    </div>

    <div class="card panel">
      <div class="panel-head">
        <h3>签到用户</h3>
        <span class="hint">{{ users.length }} 人</span>
      </div>
      <UiSkeleton v-if="loading" :rows="7" />
      <UiTable v-else :columns="columns" :data="users" empty-text="暂无签到用户" :default-sort="{ key: 'points', order: 'desc' }">
        <template #cell-user="{ row }">
          <div class="user-cell">
            <div class="avatar" :style="{ background: avatarColor(row.nickname || row.user_id) }">
              {{ esc((row.nickname || row.user_id || "?").slice(0, 1)) }}
            </div>
            <div>
              <div class="user-name">{{ esc(row.nickname || shortId(row.user_id)) }}</div>
              <div class="user-id">{{ shortId(row.user_id) }}</div>
            </div>
          </div>
        </template>
        <template #cell-role="{ row }">
          <UiTag :tone="row.role === '默认' ? 'paper' : 'navy'">{{ row.role || "默认" }}</UiTag>
        </template>
        <template #cell-points="{ row }"><span class="num">{{ fmtNum(row.points || 0) }}</span></template>
        <template #cell-affection="{ row }"><span class="num">{{ row.affection || 0 }}</span></template>
        <template #cell-streak="{ row }"><span class="num">{{ row.streak || 0 }} 天</span></template>
        <template #cell-last_checkin="{ row }">{{ row.last_checkin || "-" }}</template>
        <template #cell-share="{ row }">
          <div class="progress"><i :style="{ width: Math.round(((row.points || 0) / maxP) * 100) + '%' }"></i></div>
        </template>
      </UiTable>
    </div>
  </div>
</template>

<style scoped>
.stats-grid.small { grid-template-columns: repeat(2, 1fr); max-width: 460px; }
</style>