<script setup>
import { computed, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus, Edit, Delete } from "@element-plus/icons-vue";
import { api, esc } from "../../api";
import StatCard from "../StatCard.vue";

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
    ElMessage.error(e.message);
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
    ElMessage.warning("名称和内容不能为空");
    return;
  }
  saving.value = true;
  try {
    if (isEdit.value) {
      await api("/prompts/" + encodeURIComponent(originalName.value), {
        method: "PUT",
        body: JSON.stringify({ content }),
      });
      ElMessage.success("已更新");
    } else {
      await api("/prompts", {
        method: "POST",
        body: JSON.stringify({ name, content }),
      });
      ElMessage.success("已创建");
    }
    dlgVisible.value = false;
    await load();
  } catch (e) {
    ElMessage.error(e.message);
  } finally {
    saving.value = false;
  }
}

async function deletePrompt(name) {
  try {
    await ElMessageBox.confirm("确定要删除 Prompt \"" + name + "\" 吗？此操作不可恢复。", "删除确认", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  try {
    await api("/prompts/" + encodeURIComponent(name), { method: "DELETE" });
    ElMessage.success("已删除");
    await load();
  } catch (e) {
    ElMessage.error(e.message);
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
      <el-button type="primary" :icon="Plus" @click="openCreate">新建 Prompt</el-button>
    </div>

    <el-skeleton :loading="loading" animated :rows="6">
      <div class="prompt-list">
        <div v-for="(p, i) in entries" :key="i" class="card prompt-card">
          <div class="prompt-head">
            <h3 class="prompt-name">{{ esc(p.name) }}</h3>
            <div class="prompt-actions">
              <el-button text type="primary" :icon="Edit" @click="openEdit(p.name)">编辑</el-button>
              <el-button text type="danger" :icon="Delete" @click="deletePrompt(p.name)">删除</el-button>
            </div>
          </div>
          <p class="prompt-body">{{ esc(p.content) }}</p>
          <div class="prompt-meta">
            <span>创建：{{ p.created_at }}</span>
            <span>更新：{{ p.updated_at }}</span>
          </div>
        </div>
        <el-empty v-if="!loading && entries.length === 0" description="暂无 Prompt，点击上方按钮创建" :image-size="60" />
      </div>
    </el-skeleton>

    <el-dialog v-model="dlgVisible" :title="dlgTitle" width="560px" :close-on-click-modal="false">
      <el-form label-position="top">
        <el-form-item label="名称" v-if="!isEdit">
          <el-input v-model="dlgName" placeholder="Prompt 名称（用于引用）" maxlength="64" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input
            v-model="dlgContent"
            type="textarea"
            :rows="8"
            placeholder="输入 Prompt 内容..."
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlgVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="savePrompt">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>