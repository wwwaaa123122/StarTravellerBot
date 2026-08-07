<script setup>
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { api, esc, fmtNum } from "../../api";
import StatCard from "../StatCard.vue";

const list = ref([]);
const loading = ref(false);
const toggling = ref({});

async function load() {
  loading.value = true;
  try {
    const data = await api("/plugins/toggle");
    list.value = data.plugins || [];
  } catch (e) {
    ElMessage.error(e.message);
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
    await api("/plugins/toggle", {
      method: "PUT",
      body: JSON.stringify(body),
    });
    plugin.enabled = newVal;
    ElMessage.success(`"${name}" 已${newVal ? "启用" : "禁用"}`);
  } catch (e) {
    ElMessage.error(e.message);
    plugin.enabled = !newVal; // 回滚
  } finally {
    toggling.value[name] = false;
  }
}
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
            <span class="dot" :class="p.enabled ? 'success' : 'off'"></span>
            <span class="plugin-name">{{ esc(p.file.replace(/\.py$/, "")) }}</span>
          </div>
          <p class="plugin-desc">{{ esc(p.help || "无帮助描述") }}</p>
          <div class="plugin-meta">
            <span class="mono">{{ esc(p.file) }}</span>
            <span class="plugin-trigger">{{ esc(p.keyword || "无关键字") }}</span>
          </div>
          <div class="plugin-toggle">
            <el-switch
              :model-value="p.enabled"
              :loading="toggling[p.name]"
              active-text="启用"
              inactive-text="禁用"
              @change="(val) => togglePlugin(p, val)"
            />
          </div>
        </div>
        <el-empty v-if="!loading && list.length === 0" description="plugins/ 目录为空" :image-size="60" />
      </div>
    </el-skeleton>
  </div>
</template>