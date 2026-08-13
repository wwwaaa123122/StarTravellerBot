<script setup>
import { computed, onMounted, ref } from "vue";
import { api, esc, fmtNum } from "../../api";
import { toast } from "../../ui/toast";
import StatCard from "../StatCard.vue";
import UiSkeleton from "../ui/UiSkeleton.vue";
import UiEmpty from "../ui/UiEmpty.vue";
import UiSwitch from "../ui/UiSwitch.vue";

const list = ref([]);
const loading = ref(false);
const toggling = ref({});

async function load() {
  loading.value = true;
  try {
    const data = await api("/plugins/toggle");
    list.value = data.plugins || [];
  } catch (e) {
    toast.error(e.message);
  } finally {
    loading.value = false;
  }
}
onMounted(load);

const enabledCount = computed(() => list.value.filter((p) => p.enabled).length);
const cards = computed(() => [
  { label: "插件总数", value: fmtNum(list.value.length), sub: "plugins/ 目录", dot: "success" },
  { label: "已启用", value: fmtNum(enabledCount.value), sub: "可切换开关", dot: "success" },
]);

async function togglePlugin(plugin, newVal) {
  const name = plugin.name;
  toggling.value[name] = true;
  try {
    const body = {};
    body[name] = newVal;
    await api("/plugins/toggle", { method: "PUT", body: JSON.stringify(body) });
    plugin.enabled = newVal;
    toast.success(`"${name}" 已${newVal ? "启用" : "禁用"}`);
  } catch (e) {
    toast.error(e.message);
    plugin.enabled = !newVal;
  } finally {
    toggling.value[name] = false;
  }
}
</script>

<template>
  <div class="view-plugins">
    <div class="stats-grid small">
      <StatCard v-for="(c, i) in cards" :key="i" :label="c.label" :value="c.value" :sub="c.sub" :dot="c.dot" />
    </div>

    <UiSkeleton v-if="loading" :rows="7" />
    <div v-else class="plugin-grid">
      <div v-for="(p, i) in list" :key="i" class="card plugin-card">
        <div class="plugin-top">
          <span class="dot" :class="p.enabled ? '' : 'off'"></span>
          <span class="plugin-name">{{ esc(p.file.replace(/\.py$/, "")) }}</span>
        </div>
        <p class="plugin-desc">{{ esc(p.help || "无帮助描述") }}</p>
        <div class="plugin-meta">
          <span class="mono">{{ esc(p.file) }}</span>
          <span class="plugin-trigger">{{ esc(p.keyword || "无关键字") }}</span>
        </div>
        <div class="plugin-toggle">
          <UiSwitch
            :model-value="p.enabled"
            :loading="toggling[p.name]"
            active-text="启用"
            inactive-text="禁用"
            @change="(v) => togglePlugin(p, v)"
          />
        </div>
      </div>
      <UiEmpty v-if="!list.length" text="plugins/ 目录为空" />
    </div>
  </div>
</template>

<style scoped>
.stats-grid.small { grid-template-columns: repeat(2, 1fr); max-width: 460px; }
</style>
