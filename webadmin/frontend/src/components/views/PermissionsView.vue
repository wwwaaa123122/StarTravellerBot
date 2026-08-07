<script setup>
import { computed, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus, Delete } from "@element-plus/icons-vue";
import { api } from "../../api";
import StatCard from "../StatCard.vue";

const perm = ref({ root_users: [], blacklist: [], allow_ai: true });
const loading = ref(false);
const saving = ref(false);

// 编辑用的临时列表
const rootUsers = ref([]);
const blacklist = ref([]);
const allowAi = ref(true);

// 新增输入
const newRootUser = ref("");
const newBlacklist = ref("");

async function load() {
  loading.value = true;
  try {
    const p = await api("/permissions");
    perm.value = p;
    rootUsers.value = [...(p.root_users || [])];
    blacklist.value = [...(p.blacklist || [])];
    allowAi.value = p.allow_ai !== false;
  } catch (e) {
    ElMessage.error(e.message);
  } finally {
    loading.value = false;
  }
}
onMounted(load);

function addRootUser() {
  const v = newRootUser.value.trim();
  if (!v) return;
  if (rootUsers.value.includes(v)) {
    ElMessage.warning("该用户已存在");
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
    ElMessage.warning("该用户已在黑名单中");
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
    ElMessage.success("权限设置已保存");
    await load();
  } catch (e) {
    ElMessage.error(e.message);
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

    <el-skeleton :loading="loading" animated :rows="8">
      <div class="card panel">
        <div class="panel-head">
          <h3>管理员列表</h3>
          <span class="hint">root_users：允许使用管理员命令的用户 ID</span>
        </div>
        <div class="tag-list">
          <el-tag
            v-for="(u, i) in rootUsers"
            :key="i"
            closable
            type="primary"
            effect="dark"
            @close="removeRootUser(i)"
          >{{ u }}</el-tag>
          <el-empty v-if="rootUsers.length === 0" description="暂无管理员" :image-size="40" />
        </div>
        <div class="add-row">
          <el-input
            v-model="newRootUser"
            placeholder="输入用户 ID"
            size="small"
            style="width: 240px"
            @keyup.enter="addRootUser"
          />
          <el-button :icon="Plus" size="small" type="primary" @click="addRootUser">添加</el-button>
        </div>
      </div>

      <div class="card panel">
        <div class="panel-head">
          <h3>黑名单</h3>
          <span class="hint">black_list：禁止使用机器人的用户 ID</span>
        </div>
        <div class="tag-list">
          <el-tag
            v-for="(u, i) in blacklist"
            :key="i"
            closable
            type="danger"
            effect="dark"
            @close="removeBlacklist(i)"
          >{{ u }}</el-tag>
          <el-empty v-if="blacklist.length === 0" description="黑名单为空" :image-size="40" />
        </div>
        <div class="add-row">
          <el-input
            v-model="newBlacklist"
            placeholder="输入用户 ID"
            size="small"
            style="width: 240px"
            @keyup.enter="addBlacklist"
          />
          <el-button :icon="Plus" size="small" type="danger" @click="addBlacklist">添加</el-button>
        </div>
      </div>

      <div class="card panel">
        <div class="panel-head">
          <h3>AI 对话开关</h3>
          <span class="hint">allow_ai：控制机器人是否响应 AI 对话</span>
        </div>
        <el-switch
          v-model="allowAi"
          active-text="开启"
          inactive-text="关闭"
          size="large"
        />
      </div>

      <div class="save-bar">
        <el-button type="primary" :loading="saving" @click="save">保存设置</el-button>
      </div>
    </el-skeleton>
  </div>
</template>