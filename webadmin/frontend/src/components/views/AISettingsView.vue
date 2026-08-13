<script setup>
import { computed, onMounted, ref } from "vue";
import { api } from "../../api";
import { toast } from "../../ui/toast";
import StatCard from "../StatCard.vue";
import UiSkeleton from "../ui/UiSkeleton.vue";
import UiInput from "../ui/UiInput.vue";
import UiNumberInput from "../ui/UiNumberInput.vue";
import UiSelect from "../ui/UiSelect.vue";
import UiButton from "../ui/UiButton.vue";

const settings = ref({});
const loading = ref(false);
const saving = ref(false);

const form = ref({
  ai_model: "",
  ai_base_url: "",
  ai_max_tokens: 2000,
  ai_temperature: 0.7,
  deepseek_key: "",
  gemini_key: "",
  openai_key: "",
  enable_network: "DeepSeek",
});

const networkOptions = [
  { label: "DeepSeek", value: "DeepSeek" },
  { label: "Gemini", value: "Gemini" },
  { label: "关闭", value: "None" },
];

async function load() {
  loading.value = true;
  try {
    const s = await api("/ai-settings");
    settings.value = s;
    form.value = {
      ai_model: s.ai_model || "deepseek-v4-flash",
      ai_base_url: s.ai_base_url || "https://api.deepseek.com",
      ai_max_tokens: s.ai_max_tokens || 2000,
      ai_temperature: s.ai_temperature || 0.7,
      deepseek_key: "",
      gemini_key: "",
      openai_key: "",
      enable_network: s.enable_network || "DeepSeek",
    };
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
    const body = {
      ai_model: form.value.ai_model,
      ai_base_url: form.value.ai_base_url,
      ai_max_tokens: Number(form.value.ai_max_tokens),
      ai_temperature: Number(form.value.ai_temperature),
      EnableNetwork: form.value.enable_network,
    };
    if (form.value.deepseek_key.trim()) body.deepseek_key = form.value.deepseek_key.trim();
    if (form.value.gemini_key.trim()) body.gemini_key = form.value.gemini_key.trim();
    if (form.value.openai_key.trim()) body.openai_key = form.value.openai_key.trim();
    await api("/ai-settings", { method: "PUT", body: JSON.stringify(body) });
    toast.success("AI 设置已保存");
    await load();
  } catch (e) {
    toast.error(e.message);
  } finally {
    saving.value = false;
  }
}

const cards = computed(() => [
  { label: "AI 模型", value: settings.value.ai_model || "-", sub: "ai_model", dot: "success" },
  { label: "最大 Token", value: String(settings.value.ai_max_tokens || "-"), sub: "ai_max_tokens", dot: "success" },
  { label: "温度", value: String(settings.value.ai_temperature ?? "-"), sub: "ai_temperature", dot: "success" },
]);
</script>

<template>
  <div class="view-ai-settings">
    <div class="stats-grid small">
      <StatCard v-for="(c, i) in cards" :key="i" :label="c.label" :value="c.value" :sub="c.sub" :dot="c.dot" />
    </div>

    <UiSkeleton v-if="loading" :rows="8" />
    <template v-else>
      <div class="card panel">
        <div class="panel-head"><h3>模型配置</h3></div>
        <div class="form-grid">
          <div class="form-item">
            <label class="form-label">AI 模型</label>
            <UiInput v-model="form.ai_model" placeholder="如 deepseek-v4-flash" />
          </div>
          <div class="form-item">
            <label class="form-label">API 地址</label>
            <UiInput v-model="form.ai_base_url" placeholder="https://api.deepseek.com" />
          </div>
          <div class="form-item">
            <label class="form-label">最大 Token</label>
            <UiNumberInput v-model="form.ai_max_tokens" :min="100" :max="128000" :step="100" />
          </div>
          <div class="form-item">
            <label class="form-label">温度 (0-2)</label>
            <UiNumberInput v-model="form.ai_temperature" :min="0" :max="2" :step="0.1" :precision="1" />
          </div>
          <div class="form-item">
            <label class="form-label">联网搜索</label>
            <UiSelect v-model="form.enable_network" :options="networkOptions" />
          </div>
        </div>
      </div>

      <div class="card panel">
        <div class="panel-head">
          <h3>API 密钥</h3>
          <span class="hint">留空则不修改，密钥仅保存时更新</span>
        </div>
        <div class="form-grid">
          <div class="form-item">
            <label class="form-label">DeepSeek Key</label>
            <UiInput v-model="form.deepseek_key" type="password" show-password placeholder="留空保持不变" />
          </div>
          <div class="form-item">
            <label class="form-label">Gemini Key</label>
            <UiInput v-model="form.gemini_key" type="password" show-password placeholder="留空保持不变" />
          </div>
          <div class="form-item">
            <label class="form-label">OpenAI Key</label>
            <UiInput v-model="form.openai_key" type="password" show-password placeholder="留空保持不变" />
          </div>
        </div>
      </div>

      <div class="save-bar">
        <UiButton :loading="saving" @click="save">保存设置</UiButton>
      </div>
    </template>
  </div>
</template>

<style scoped>
.stats-grid.small { grid-template-columns: repeat(3, 1fr); max-width: 720px; }
.view-ai-settings .card { margin-bottom: 16px; }
@media (max-width: 720px) {
  .stats-grid.small { grid-template-columns: repeat(1, 1fr); max-width: none; }
}
</style>
