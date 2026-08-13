<script setup>
import { computed, onMounted, ref } from "vue";
import { api, esc, fmtNum } from "../../api";
import { toast } from "../../ui/toast";
import StatCard from "../StatCard.vue";
import UiSkeleton from "../ui/UiSkeleton.vue";
import UiSwitch from "../ui/UiSwitch.vue";
import UiTextarea from "../ui/UiTextarea.vue";
import UiMultiSelect from "../ui/UiMultiSelect.vue";
import UiButton from "../ui/UiButton.vue";
import UiTag from "../ui/UiTag.vue";
import Icon from "../Icon.vue";

const sc = ref({});
const groupOptions = ref([]);
const loading = ref(false);
const saving = ref(false);
const sending = ref(false);

const form = ref({ enabled: true, send_time: "06:00", content: "", groups: [] });
const sendForm = ref({ content: "", groups: [] });

async function load() {
  loading.value = true;
  try {
    const [s, u] = await Promise.all([api("/schedule"), api("/usage")]);
    sc.value = s;
    groupOptions.value = u.groups || [];
    form.value = {
      enabled: s.enabled !== false,
      send_time: s.send_time || "06:00",
      content: s.content || "",
      groups: [...(s.channels || [])],
    };
    sendForm.value = { content: s.content || "", groups: [] };
  } catch (e) {
    toast.error(e.message);
  } finally {
    loading.value = false;
  }
}
onMounted(load);

async function save() {
  saving.value = true;
  try {
    await api("/schedule", {
      method: "PUT",
      body: JSON.stringify({
        enabled: form.value.enabled,
        send_time: form.value.send_time,
        content: form.value.content,
        groups: form.value.groups,
      }),
    });
    toast.success("定时发送配置已保存");
    await load();
  } catch (e) {
    toast.error(e.message);
  } finally {
    saving.value = false;
  }
}

async function sendNow() {
  sending.value = true;
  try {
    const body = { content: sendForm.value.content };
    if (sendForm.value.groups.length) body.groups = sendForm.value.groups;
    const r = await api("/schedule/send", { method: "POST", body: JSON.stringify(body) });
    if (r.ok) {
      if (typeof r.sent === "number") {
        toast.success(`群发完成：成功 ${r.sent}，失败 ${r.failed || 0}`);
        const fails = (r.results || []).filter((x) => !x.ok);
        if (fails.length) {
          toast.warning("失败群: " + fails.map((x) => `${x.group}: ${x.error || "发送失败"}`).join("；"));
        }
      } else {
        toast.success(r.message || "已触发立即群发");
      }
    } else {
      toast.error(r.message || "发送失败");
    }
  } catch (e) {
    toast.error(e.message);
  } finally {
    sending.value = false;
  }
}

const cards = computed(() => [
  { label: "任务状态", value: sc.value.enabled ? "已启用" : "已停用", sub: "scheduled_send 配置", dot: sc.value.enabled ? "success" : "off" },
  { label: "发送时间", value: sc.value.send_time || "-", sub: "每日定时", dot: "success" },
  { label: "今日状态", value: sc.value.today_done ? "已发送" : "待发送", sub: "上次发送 " + (sc.value.last_sent || "-"), dot: sc.value.today_done ? "success" : "off" },
  { label: "目标群", value: fmtNum((sc.value.channels || []).length), sub: "group_openid", dot: "success" },
]);
</script>

<template>
  <div class="view-schedule">
    <div class="stats-grid small">
      <StatCard v-for="(c, i) in cards" :key="i" :label="c.label" :value="c.value" :sub="c.sub" :dot="c.dot" />
    </div>

    <UiSkeleton v-if="loading" :rows="9" />
    <template v-else>
      <div class="card panel">
        <div class="panel-head"><h3>定时发送配置</h3></div>
        <div class="form-grid">
          <div class="form-item">
            <label class="form-label">启用定时群发</label>
            <UiSwitch v-model="form.enabled" active-text="启用" inactive-text="停用" />
          </div>
          <div class="form-item">
            <label class="form-label">发送时间</label>
            <div class="time-wrap">
              <Icon name="clock" :size="15" class="time-ic" />
              <input v-model="form.send_time" type="time" class="time-input" step="300" />
            </div>
          </div>
          <div class="form-item full">
            <label class="form-label">发送内容</label>
            <UiTextarea v-model="form.content" :rows="2" placeholder="如：早生蚝" />
          </div>
          <div class="form-item full">
            <label class="form-label">目标群 (group_openid)</label>
            <UiMultiSelect
              v-model="form.groups"
              :options="groupOptions"
              allow-create
              clearable
              placeholder="选择或输入群 openid 后回车"
              no-data-text="暂无使用过 bot 的群记录，可直接输入群 openid 后回车"
            />
          </div>
        </div>
        <div class="save-bar">
          <UiButton :loading="saving" @click="save">保存配置</UiButton>
        </div>
      </div>

      <div class="card panel">
        <div class="panel-head">
          <h3>立即群发</h3>
          <span class="hint">留空内容则使用定时发送内容，留空群则发送到已配置的目标群</span>
        </div>
        <div class="form-grid">
          <div class="form-item full">
            <label class="form-label">发送内容</label>
            <UiTextarea v-model="sendForm.content" :rows="2" placeholder="留空使用定时发送内容" />
          </div>
          <div class="form-item full">
            <label class="form-label">目标群 (可选)</label>
            <UiMultiSelect
              v-model="sendForm.groups"
              :options="groupOptions"
              allow-create
              clearable
              placeholder="留空则发送到定时发送配置的群"
              no-data-text="暂无使用过 bot 的群记录，可直接输入群 openid 后回车"
            />
          </div>
        </div>
        <div class="save-bar">
          <UiButton variant="danger" icon="send" :loading="sending" @click="sendNow">立即群发</UiButton>
        </div>
      </div>

      <div class="card panel">
        <div class="panel-head"><h3>当前配置</h3></div>
        <div class="detail-grid">
          <div class="detail-item"><span class="detail-key">enabled</span><span class="detail-val" :class="sc.enabled ? 'ok' : 'bad'">{{ sc.enabled ? "true" : "false" }}</span></div>
          <div class="detail-item"><span class="detail-key">send_time</span><span class="detail-val mono">{{ esc(sc.send_time || "-") }}</span></div>
          <div class="detail-item"><span class="detail-key">last_sent</span><span class="detail-val mono">{{ esc(sc.last_sent || "-") }}</span></div>
          <div class="detail-item"><span class="detail-key">today_done</span><span class="detail-val" :class="sc.today_done ? 'ok' : ''">{{ sc.today_done ? "true" : "false" }}</span></div>
          <div class="detail-item full">
            <span class="detail-key">发送内容</span>
            <span class="detail-val">{{ esc(sc.content || "-") }}</span>
          </div>
          <div class="detail-item full">
            <span class="detail-key">目标群</span>
            <span class="detail-val">
              <span class="chips-inline">
                <UiTag v-for="(c, i) in sc.channels || []" :key="i" tone="navy" class="mono">{{ esc(c) }}</UiTag>
                <span v-if="!(sc.channels || []).length">-</span>
              </span>
            </span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.stats-grid.small { grid-template-columns: repeat(4, 1fr); }
.view-schedule .card { margin-bottom: 16px; }
.form-item.full { grid-column: 1 / -1; }
.time-wrap {
  position: relative;
  display: flex;
  align-items: center;
}
.time-ic { position: absolute; left: 12px; color: var(--ink-3); pointer-events: none; }
.time-input {
  width: 100%;
  border: 1px solid var(--line-strong);
  border-radius: 9px;
  background: var(--surface);
  color: var(--ink);
  font-family: var(--font-mono);
  font-size: 13.5px;
  padding: 9px 12px 9px 34px;
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.time-input:focus {
  border-color: var(--vermilion);
  box-shadow: 0 0 0 3px rgba(192, 57, 43, 0.12);
}
.chips-inline { display: inline-flex; flex-wrap: wrap; gap: 6px; justify-content: flex-end; }
@media (max-width: 900px) {
  .stats-grid.small { grid-template-columns: repeat(2, 1fr); }
}
</style>
