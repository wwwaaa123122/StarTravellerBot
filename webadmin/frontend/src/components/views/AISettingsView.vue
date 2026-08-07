<script setup>
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "../../api";
import StatCard from "../StatCard.vue";

const settings = ref({});
const loading = ref(false);
const saving = ref(false);

// 编辑用的表单数据
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
    ElMessage.error(e.message);
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
    // 只在用户输入了新密钥时才发送
    if (form.value.deepseek_key.trim()) body.deepseek_key = form.value.deepseek_key.trim();
    if (form.value.gemini_key.trim()) body.gemini_key = form.value.gemini_key.trim();
    if (form.value.openai_key.trim()) body.openai_key = form.value.openai_key.trim();
    await api("/ai-settings", {
      method: "PUT",
      body: JSON.stringify(body),
    });
    ElMessage.success("AI 设置已保存");
    await load();
  } catch (e) {
    ElMessage.error(e.message);
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

    <el-skeleton :loading="loading" animated :rows="10">
      <div class="card panel">
        <div class="panel-head"><h3>模型配置</h3></div>
        <div class="form-grid">
          <div class="form-item">
            <label class="form-label">AI 模型</label>
            <el-input v-model="form.ai_model" placeholder="如 deepseek-v4-flash" />
          </div>
          <div class="form-item">
            <label class="form-label">API 地址</label>
            <el-input v-model="form.ai_base_url" placeholder="https://api.deepseek.com" />
          </div>
          <div class="form-item">
            <label class="form-label">最大 Token</label>
            <el-input-number v-model="form.ai_max_tokens" :min="100" :max="128000" :step="100" style="width: 100%" />
          </div>
          <div class="form-item">
            <label class="form-label">温度 (0-2)</label>
            <el-input-number v-model="form.ai_temperature" :min="0" :max="2" :step="0.1" :precision="1" style="width: 100%" />
          </div>
          <div class="form-item">
            <label class="form-label">联网搜索</label>
            <el-select v-model="form.enable_network" style="width: 100%">
              <el-option label="DeepSeek" value="DeepSeek" />
              <el-option label="Gemini" value="Gemini" />
              <el-option label="关闭" value="None" />
            </el-select>
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
            <el-input v-model="form.deepseek_key" type="password" show-password placeholder="留空保持不变" />
          </div>
          <div class="form-item">
            <label class="form-label">Gemini Key</label>
            <el-input v-model="form.gemini_key" type="password" show-password placeholder="留空保持不变" />
          </div>
          <div class="form-item">
            <label class="form-label">OpenAI Key</label>
            <el-input v-model="form.openai_key" type="password" show-password placeholder="留空保持不变" />
          </div>
        </div>
      </div>

      <div class="save-bar">
        <el-button type="primary" :loading="saving" @click="save">保存设置</el-button>
      </div>
    </el-skeleton>
  </div>
</template>