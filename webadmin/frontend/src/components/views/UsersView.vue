<script setup>
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { api, fmtNum, shortId, esc } from "../../api";
import StatCard from "../StatCard.vue";

const users = ref([]);
const loading = ref(false);

async function load() {
  loading.value = true;
  try {
    const res = await api("/users");
    users.value = (res.users || []).slice().sort((a, b) => (b.points || 0) - (a.points || 0));
  } catch (e) {
    ElMessage.error(e.message);
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

function avatarColor(ch) {
  const palette = ["#6366f1", "#a855f7", "#22d3ee", "#34d399", "#fbbf24", "#fb7185", "#38bdf8", "#f97316"];
  return palette[(ch || "?").charCodeAt(0) % palette.length];
}
</script>

<template>
  <div class="view-users">
    <div class="stats-grid small">
      <StatCard
        v-for="(c, i) in cards"
        :key="i"
        :label="c.label"
        :value="c.value"
        :sub="c.sub"
        :dot="c.dot"
      />
    </div>

    <div class="card panel">
      <div class="panel-head">
        <h3>签到用户（{{ users.length }}）</h3>
      </div>
      <el-table :data="users" v-loading="loading" class="pretty-table">
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
        <el-table-column label="角色" width="110">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ row.role || "默认" }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="积分" width="110" sortable prop="points">
          <template #default="{ row }">{{ fmtNum(row.points || 0) }}</template>
        </el-table-column>
        <el-table-column prop="affection" label="好感度" width="100">
          <template #default="{ row }">{{ row.affection || 0 }}</template>
        </el-table-column>
        <el-table-column label="连续天数" width="110">
          <template #default="{ row }">{{ row.streak || 0 }} 天</template>
        </el-table-column>
        <el-table-column label="最后签到" min-width="140">
          <template #default="{ row }">{{ row.last_checkin || "-" }}</template>
        </el-table-column>
        <el-table-column label="积分占比" min-width="140">
          <template #default="{ row }">
            <div class="progress">
              <i :style="{ width: Math.round(((row.points || 0) / maxP) * 100) + '%' }"></i>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无签到用户" :image-size="60" />
        </template>
      </el-table>
    </div>
  </div>
</template>
