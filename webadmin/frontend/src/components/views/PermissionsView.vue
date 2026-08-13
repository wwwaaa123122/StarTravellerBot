<script setup>
import { computed, onMounted, ref } from "vue";
import { api } from "../../api";
import { toast } from "../../ui/toast";
import StatCard from "../StatCard.vue";
import UiSkeleton from "../ui/UiSkeleton.vue";
import UiInput from "../ui/UiInput.vue";
import UiButton from "../ui/UiButton.vue";
import UiTag from "../ui/UiTag.vue";
import UiSwitch from "../ui/UiSwitch.vue";
import UiEmpty from "../ui/UiEmpty.vue";

const loading = ref(false);
const saving = ref(false);

const rootUsers = ref([]);
const blacklist = ref([]);
const allowAi = ref(true);

const newRootUser = ref("");
const newBlacklist = ref("");

async function load() {
  loading.value = true;
  try {
    const p = await api("/permissions");
    rootUsers.value = [...(p.root_users || [])];
    blacklist.value = [...(p.blacklist || [])];
    allowAi.value = p.allow_ai !== false;
  } catch (e) {
    toast.error(e.message);
  } finally {
    loading.value = false;
  }
}
onMounted(load);

function addRootUser() {
  const v = newRootUser.value.trim();
  if (!v) return;
  if (rootUsers.value.includes(v)) {
    toast.warning("该用户已存在");
    return;
  }
  rootUsers.value.push(v);
  newRootUser.value = "";
}
function removeRootUser(idx) {
  rootUsers.value.splice(idx, 1);
}
function addBlacklist() {
  const v = newBlacklist.value.trim();
  if (!v) return;
  if (blacklist.value.includes(v)) {
    toast.warning("该用户已在黑名单中");
    return;
  }
  blacklist.value.push(v);
  newBlacklist.value = "";
}
function removeBlacklist(idx) {
  blacklist.value.splice(idx, 1);
}

async function save() {
  saving.value = true;
  try {
    await api("/permissions", {
      method: "PUT",
      body: JSON.stringify({
        root_users: rootUsers.value,
        blacklist: blacklist.value,
        allow_ai: allowAi.value,
      }),
    });
    toast.success("权限设置已保存");
    await load();
  } catch (e) {
    toast.error(e.message);
  } finally {
    saving.value = false;
  }
}

const cards = computed(() => [
  { label: "管理员数量", value: String(rootUsers.value.length), sub: "root_users", dot: "success" },
  { label: "黑名单数量", value: String(blacklist.value.length), sub: "black_list", dot: blacklist.value.length > 0 ? "off" : "success" },
  { label: "AI 对话", value: allowAi.value ? "已开启" : "已关闭", sub: "allow_ai", dot: allowAi.value ? "success" : "off" },
]);
</script>

<template>
  <div class="view-permissions">
    <div class="stats-grid small">
      <StatCard v-for="(c, i) in cards" :key="i" :label="c.label" :value="c.value" :sub="c.sub" :dot="c.dot" />
    </div>

    <UiSkeleton v-if="loading" :rows="7" />
    <template v-else>
      <div class="card panel">
        <div class="panel-head">
          <h3>管理员列表</h3>
          <span class="hint">root_users：允许使用管理员命令的用户 ID</span>
        </div>
        <div class="tag-list">
          <UiTag v-for="(u, i) in rootUsers" :key="i" tone="red" closable @close="removeRootUser(i)">{{ u }}</UiTag>
          <UiEmpty v-if="!rootUsers.length" text="暂无管理员" />
        </div>
        <div class="add-row">
          <UiInput v-model="newRootUser" size="sm" placeholder="输入用户 ID" style="width: 250px" @enter="addRootUser" />
          <UiButton size="sm" icon="plus" @click="addRootUser">添加</UiButton>
        </div>
      </div>

      <div class="card panel">
        <div class="panel-head">
          <h3>黑名单</h3>
          <span class="hint">black_list：禁止使用机器人的用户 ID</span>
        </div>
        <div class="tag-list">
          <UiTag v-for="(u, i) in blacklist" :key="i" tone="red" closable @close="removeBlacklist(i)">{{ u }}</UiTag>
          <UiEmpty v-if="!blacklist.length" text="黑名单为空" />
        </div>
        <div class="add-row">
          <UiInput v-model="newBlacklist" size="sm" placeholder="输入用户 ID" style="width: 250px" @enter="addBlacklist" />
          <UiButton size="sm" variant="danger" icon="plus" @click="addBlacklist">添加</UiButton>
        </div>
      </div>

      <div class="card panel">
        <div class="panel-head">
          <h3>AI 对话开关</h3>
          <span class="hint">allow_ai：控制机器人是否响应 AI 对话</span>
        </div>
        <UiSwitch v-model="allowAi" size="lg" active-text="开启" inactive-text="关闭" />
      </div>

      <div class="save-bar">
        <UiButton :loading="saving" @click="save">保存设置</UiButton>
      </div>
    </template>
  </div>
</template>

<style scoped>
.stats-grid.small { grid-template-columns: repeat(3, 1fr); max-width: 720px; }
.view-permissions .card { margin-bottom: 16px; }
@media (max-width: 720px) {
  .stats-grid.small { grid-template-columns: repeat(1, 1fr); max-width: none; }
}
</style>
