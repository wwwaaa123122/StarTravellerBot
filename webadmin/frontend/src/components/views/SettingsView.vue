<script setup>
import { computed, onMounted, ref } from "vue";
import { api, esc } from "../../api";
import { toast } from "../../ui/toast";
import StatCard from "../StatCard.vue";
import UiSkeleton from "../ui/UiSkeleton.vue";

const cfg = ref({});
const st = ref({});
const loading = ref(false);

async function load() {
  loading.value = true;
  try {
    const [c, s] = await Promise.all([api("/config"), api("/status")]);
    cfg.value = c;
    st.value = s;
  } catch (e) {
    toast.error(e.message);
  } finally {
    loading.value = false;
  }
}
onMounted(load);

const bi = computed(() => cfg.value.bot_info || {});
const sys = computed(() => st.value.status || {});
const bot = computed(() => st.value.bot || {});
const configEntries = computed(() => Object.entries(cfg.value.config || {}));

const cards = computed(() => [
  { label: "机器人名称", value: bi.value.name || "-", sub: "来自 .env", dot: "success" },
  { label: "运行状态", value: bot.value.running ? "运行中" : "未运行", sub: "PID " + (bot.value.pid || "-"), dot: bot.value.running ? "success" : "off" },
]);

function fmtValue(v) {
  if (v === null || v === undefined) return "-";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}
</script>

<template>
  <div class="view-settings">
    <div class="stats-grid small">
      <StatCard v-for="(c, i) in cards" :key="i" :label="c.label" :value="c.value" :sub="c.sub" :dot="c.dot" />
    </div>

    <UiSkeleton v-if="loading" :rows="8" />
    <template v-else>
      <div class="card panel">
        <div class="panel-head"><h3>机器人信息</h3><span class="hint">敏感字段已脱敏</span></div>
        <div class="detail-grid">
          <div class="detail-item"><span class="detail-key">bot_name</span><span class="detail-val">{{ esc(bi.name || "-") }}</span></div>
          <div class="detail-item"><span class="detail-key">log_level</span><span class="detail-val mono">{{ esc(bi.log_level || "-") }}</span></div>
          <div class="detail-item"><span class="detail-key">appid</span><span class="detail-val mono">{{ esc(bi.openqq_appid || "-") }}</span></div>
          <div class="detail-item"><span class="detail-key">config_path</span><span class="detail-val mono">{{ esc(bi.config_path || "-") }}</span></div>
          <div class="detail-item"><span class="detail-key">后端版本</span><span class="detail-val mono">{{ esc(cfg.version || "-") }}</span></div>
        </div>
      </div>

      <div class="card panel">
        <div class="panel-head"><h3>运行配置（脱敏）</h3></div>
        <div class="detail-grid">
          <div v-for="([k, v], i) in configEntries" :key="i" class="detail-item">
            <span class="detail-key">{{ esc(k) }}</span>
            <span class="detail-val mono">{{ esc(fmtValue(v)) }}</span>
          </div>
          <div v-if="configEntries.length === 0" class="detail-item full">
            <span class="detail-val">.env 为空或未找到</span>
          </div>
        </div>
      </div>

      <div class="card panel">
        <div class="panel-head"><h3>系统环境</h3></div>
        <div class="detail-grid">
          <div class="detail-item"><span class="detail-key">uptime</span><span class="detail-val">{{ esc(sys.uptime_text || "-") }}</span></div>
          <div class="detail-item"><span class="detail-key">python</span><span class="detail-val mono">{{ esc(sys.python || "-") }}</span></div>
          <div class="detail-item"><span class="detail-key">platform</span><span class="detail-val mono">{{ esc(sys.platform || "-") }}</span></div>
          <div class="detail-item"><span class="detail-key">webadmin_mem</span><span class="detail-val mono">{{ sys.webadmin_mem_mb || 0 }} MB</span></div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.stats-grid.small { grid-template-columns: repeat(2, 1fr); max-width: 460px; }
.view-settings .card { margin-bottom: 16px; }
.detail-item.full { grid-column: 1 / -1; }
</style>