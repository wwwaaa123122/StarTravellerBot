<script setup>
import { computed, onMounted, ref } from "vue";
import { api, esc } from "../../api";
import { toast } from "../../ui/toast";
import { confirm } from "../../ui/modal";
import StatCard from "../StatCard.vue";
import UiSkeleton from "../ui/UiSkeleton.vue";
import UiEmpty from "../ui/UiEmpty.vue";
import UiInput from "../ui/UiInput.vue";
import UiTextarea from "../ui/UiTextarea.vue";
import UiButton from "../ui/UiButton.vue";
import UiModal from "../ui/UiModal.vue";

const prompts = ref({});
const loading = ref(false);
const saving = ref(false);

const dlgVisible = ref(false);
const dlgTitle = ref("新建 Prompt");
const dlgName = ref("");
const dlgContent = ref("");
const isEdit = ref(false);
const originalName = ref("");

async function load() {
  loading.value = true;
  try {
    const p = await api("/prompts");
    prompts.value = p.prompts || {};
  } catch (e) {
    toast.error(e.message);
  } finally {
    loading.value = false;
  }
}
onMounted(load);

function openCreate() {
  dlgTitle.value = "新建 Prompt";
  dlgName.value = "";
  dlgContent.value = "";
  isEdit.value = false;
  originalName.value = "";
  dlgVisible.value = true;
}

function openEdit(name) {
  const p = prompts.value[name];
  if (!p) return;
  dlgTitle.value = "编辑 Prompt";
  dlgName.value = name;
  dlgContent.value = p.content || "";
  isEdit.value = true;
  originalName.value = name;
  dlgVisible.value = true;
}

async function savePrompt() {
  const name = dlgName.value.trim();
  const content = dlgContent.value.trim();
  if (!name || !content) {
    toast.warning("名称和内容不能为空");
    return;
  }
  saving.value = true;
  try {
    if (isEdit.value) {
      await api("/prompts/" + encodeURIComponent(originalName.value), {
        method: "PUT",
        body: JSON.stringify({ content }),
      });
      toast.success("已更新");
    } else {
      await api("/prompts", {
        method: "POST",
        body: JSON.stringify({ name, content }),
      });
      toast.success("已创建");
    }
    dlgVisible.value = false;
    await load();
  } catch (e) {
    toast.error(e.message);
  } finally {
    saving.value = false;
  }
}

async function deletePrompt(name) {
  const ok = await confirm({
    title: "删除确认",
    message: `确定要删除 Prompt "${name}" 吗？此操作不可恢复。`,
    confirmText: "删除",
    danger: true,
  });
  if (!ok) return;
  try {
    await api("/prompts/" + encodeURIComponent(name), { method: "DELETE" });
    toast.success("已删除");
    await load();
  } catch (e) {
    toast.error(e.message);
  }
}

const entries = computed(() => {
  return Object.entries(prompts.value).map(([name, p]) => ({
    name,
    content: p.content || "",
    created_at: p.created_at ? new Date(p.created_at * 1000).toLocaleString("zh-CN") : "-",
    updated_at: p.updated_at ? new Date(p.updated_at * 1000).toLocaleString("zh-CN") : "-",
  }));
});

const cards = computed(() => [
  { label: "Prompt 数量", value: String(entries.value.length), sub: "系统提示词", dot: "success" },
]);
</script>

<template>
  <div class="view-prompts">
    <div class="stats-grid small">
      <StatCard v-for="(c, i) in cards" :key="i" :label="c.label" :value="c.value" :sub="c.sub" :dot="c.dot" />
    </div>

    <div style="margin-bottom: 16px">
      <UiButton icon="plus" @click="openCreate">新建 Prompt</UiButton>
    </div>

    <UiSkeleton v-if="loading" :rows="6" />
    <div v-else class="prompt-list">
      <div v-for="(p, i) in entries" :key="i" class="card prompt-card">
        <div class="prompt-head">
          <h3 class="prompt-name">{{ esc(p.name) }}</h3>
          <div class="prompt-actions">
            <UiButton variant="text" size="sm" icon="edit" @click="openEdit(p.name)">编辑</UiButton>
            <UiButton variant="text" size="sm" icon="trash" danger @click="deletePrompt(p.name)">删除</UiButton>
          </div>
        </div>
        <p class="prompt-body">{{ esc(p.content) }}</p>
        <div class="prompt-meta">
          <span>创建：{{ p.created_at }}</span>
          <span>更新：{{ p.updated_at }}</span>
        </div>
      </div>
      <UiEmpty v-if="!entries.length" text="暂无 Prompt，点击上方按钮创建" />
    </div>

    <UiModal v-model="dlgVisible" :title="dlgTitle" width="560">
      <div class="form-grid single">
        <div v-if="!isEdit" class="form-item">
          <label class="form-label">名称</label>
          <UiInput v-model="dlgName" placeholder="Prompt 名称（用于引用）" maxlength="64" />
        </div>
        <div class="form-item">
          <label class="form-label">内容</label>
          <UiTextarea v-model="dlgContent" :rows="9" placeholder="输入 Prompt 内容..." />
        </div>
      </div>
      <template #footer>
        <UiButton variant="ghost" @click="dlgVisible = false">取消</UiButton>
        <UiButton :loading="saving" @click="savePrompt">保存</UiButton>
      </template>
    </UiModal>
  </div>
</template>

<style scoped>
.stats-grid.small { grid-template-columns: repeat(1, 1fr); max-width: 220px; }
.form-grid.single { grid-template-columns: 1fr; }
</style>
