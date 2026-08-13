<script setup>
import { computed, onMounted, ref } from "vue";
import { api, fmtNum, shortId, esc, fmtTime } from "../../api";
import { toast } from "../../ui/toast";
import StatCard from "../StatCard.vue";
import UiSkeleton from "../ui/UiSkeleton.vue";
import UiEmpty from "../ui/UiEmpty.vue";
import UiTag from "../ui/UiTag.vue";

const mem = ref({});
const loading = ref(false);

async function load() {
  loading.value = true;
  try {
    mem.value = await api("/memory");
  } catch (e) {
    toast.error(e.message);
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
      <StatCard v-for="(c, i) in cards" :key="i" :label="c.label" :value="c.value" :sub="c.sub" :dot="c.dot" />
    </div>

    <div class="card panel">
      <div class="panel-head">
        <h3>全部记忆</h3>
        <span class="hint">最近更新在前</span>
      </div>
      <UiSkeleton v-if="loading" :rows="7" />
      <div v-else class="mem-list">
        <div v-for="(r, i) in recs" :key="i" class="mem-item">
          <div class="mem-q">{{ esc(r.question || "") }}</div>
          <div class="mem-a">{{ esc(r.answer || "") }}</div>
          <div class="mem-meta">
            <UiTag tone="navy">{{ shortId(r.user_id) }}</UiTag>
            <span>{{ fmtTime(r.ts, true) }}</span>
          </div>
        </div>
        <UiEmpty v-if="!recs.length" text="暂无记忆" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.stats-grid.small { grid-template-columns: repeat(2, 1fr); max-width: 460px; }
</style>