<script setup>
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { api, esc, fmtNum } from "../../api";
import StatCard from "../StatCard.vue";

const list = ref([]);
const loading = ref(false);

async function load() {
  loading.value = true;
  try {
    const pl = await api("/plugins");
    list.value = pl.plugins || [];
  } catch (e) {
    ElMessage.error(e.message);
  } finally {
    loading.value = false;
  }
}
onMounted(load);

const parsedCount = computed(() => list.value.filter((p) => p.keyword || p.help).length);
const cards = computed(() => [
  { label: "插件总数", value: fmtNum(list.value.length), sub: "plugins/ 目录", dot: "success" },
  { label: "已解析", value: fmtNum(parsedCount.value), sub: "含关键字/帮助", dot: "success" },
]);
</script>

<template>
  <div class="view-plugins">
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

    <el-skeleton :loading="loading" animated :rows="6">
      <div class="plugin-grid">
        <div v-for="(p, i) in list" :key="i" class="card plugin-card">
          <div class="plugin-top">
            <span class="dot success"></span>
            <span class="plugin-name">{{ esc(p.file.replace(/\.py$/, "")) }}</span>
            <span class="plugin-trigger">{{ esc(p.keyword || "无关键字") }}</span>
          </div>
          <p class="plugin-desc">{{ esc(p.help || "无帮助描述") }}</p>
          <div class="plugin-meta"><span class="mono">{{ esc(p.file) }}</span></div>
        </div>
        <el-empty v-if="!loading && list.length === 0" description="plugins/ 目录为空" :image-size="60" />
      </div>
    </el-skeleton>
  </div>
</template>
