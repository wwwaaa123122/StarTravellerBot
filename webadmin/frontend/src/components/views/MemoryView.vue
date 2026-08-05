<script setup>
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { api, fmtNum, shortId, esc, fmtTime } from "../../api";
import StatCard from "../StatCard.vue";

const mem = ref({});
const loading = ref(false);

async function load() {
  loading.value = true;
  try {
    mem.value = await api("/memory");
  } catch (e) {
    ElMessage.error(e.message);
  } finally {
    loading.value = false;
  }
}
onMounted(load);

const recs = computed(() => mem.value.records || []);
const userCount = computed(() => (Array.isArray(mem.value.users) ? mem.value.users.length : mem.value.users || 0));
const cards = computed(() => [
  { label: "记忆总数", value: fmtNum(recs.value.length), sub: "RAG 长期记忆", dot: "success" },
  { label: "关联用户", value: fmtNum(userCount.value), sub: "独立用户", dot: "success" },
]);
</script>

<template>
  <div class="view-memory">
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
        <h3>全部记忆</h3>
        <span class="hint">最近更新在前</span>
      </div>
      <el-skeleton :loading="loading" animated :rows="6">
        <div class="mem-list">
          <div v-for="(r, i) in recs" :key="i" class="mem-item">
            <div class="mem-q">{{ esc(r.question || "") }}</div>
            <div class="mem-a">{{ esc(r.answer || "") }}</div>
            <div class="mem-meta">
              <el-tag size="small" effect="plain" class="badge badge-src">{{ shortId(r.user_id) }}</el-tag>
              <span>{{ fmtTime(r.ts, true) }}</span>
            </div>
          </div>
          <el-empty v-if="!loading && recs.length === 0" description="暂无记忆" :image-size="60" />
        </div>
      </el-skeleton>
    </div>
  </div>
</template>
