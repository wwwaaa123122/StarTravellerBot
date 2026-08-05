<script setup>
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { api, esc, fmtNum } from "../../api";
import StatCard from "../StatCard.vue";

const sc = ref({});
const loading = ref(false);

async function load() {
  loading.value = true;
  try {
    sc.value = await api("/schedule");
  } catch (e) {
    ElMessage.error(e.message);
  } finally {
    loading.value = false;
  }
}
onMounted(load);

const cards = computed(() => [
  { label: "任务状态", value: sc.value.enabled ? "已启用" : "已停用", sub: "scheduled_send 配置", dot: sc.value.enabled ? "success" : "off" },
  { label: "发送时间", value: sc.value.send_time || "-", sub: "每日定时", dot: "success" },
  { label: "今日状态", value: sc.value.today_done ? "已发送" : "待发送", sub: "上次发送 " + (sc.value.last_sent || "-"), dot: sc.value.today_done ? "success" : "off" },
  { label: "目标频道", value: fmtNum((sc.value.channels || []).length), sub: "channel id", dot: "success" },
]);
</script>

<template>
  <div class="view-schedule">
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
      <div class="card panel">
        <div class="panel-head"><h3>定时发送配置</h3></div>
        <div class="detail-grid">
          <div class="detail-item">
            <span class="detail-key">enabled</span>
            <span class="detail-val">{{ sc.enabled ? "true" : "false" }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-key">send_time</span>
            <span class="detail-val mono">{{ esc(sc.send_time || "-") }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-key">last_sent</span>
            <span class="detail-val mono">{{ esc(sc.last_sent || "-") }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-key">today_done</span>
            <span class="detail-val">{{ sc.today_done ? "true" : "false" }}</span>
          </div>
        </div>
        <div class="detail-grid">
          <div class="detail-item full">
            <span class="detail-key">发送内容</span>
            <span class="detail-val">{{ esc(sc.content || "-") }}</span>
          </div>
        </div>
        <div class="detail-grid">
          <div class="detail-item full">
            <span class="detail-key">目标频道</span>
            <span class="detail-val">
              <el-tag
                v-for="(c, i) in sc.channels || []"
                :key="i"
                size="small"
                effect="plain"
                class="badge badge-src mono"
              >{{ esc(c) }}</el-tag>
              <span v-if="!(sc.channels || []).length">-</span>
            </span>
          </div>
        </div>
      </div>
    </el-skeleton>
  </div>
</template>
