<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh, Sunny, Moon, Expand, Fold, SwitchButton } from "@element-plus/icons-vue";
import { store, viewTitle, setTheme, logout } from "../store";
import Sidebar from "./Sidebar.vue";
import DashboardView from "./views/DashboardView.vue";
import UsersView from "./views/UsersView.vue";
import MemoryView from "./views/MemoryView.vue";
import PluginsView from "./views/PluginsView.vue";
import PermissionsView from "./views/PermissionsView.vue";
import ScheduleView from "./views/ScheduleView.vue";
import AISettingsView from "./views/AISettingsView.vue";
import PromptsView from "./views/PromptsView.vue";
import SettingsView from "./views/SettingsView.vue";

const views = {
  dashboard: DashboardView,
  users: UsersView,
  memory: MemoryView,
  plugins: PluginsView,
  permissions: PermissionsView,
  schedule: ScheduleView,
  "ai-settings": AISettingsView,
  prompts: PromptsView,
  settings: SettingsView,
};

const collapsed = ref(localStorage.getItem("st_sidebar_collapsed") === "1");
const drawer = ref(false);
const refreshKey = ref(0);
const isMobile = ref(window.innerWidth < 820);
const now = ref(new Date());
let timer = null;

function onResize() {
  isMobile.value = window.innerWidth < 820;
}
onMounted(() => {
  timer = setInterval(() => (now.value = new Date()), 1000);
  window.addEventListener("resize", onResize);
});
onBeforeUnmount(() => {
  clearInterval(timer);
  window.removeEventListener("resize", onResize);
});

function toggleSidebar() {
  if (isMobile.value) {
    drawer.value = true;
  } else {
    collapsed.value = !collapsed.value;
    localStorage.setItem("st_sidebar_collapsed", collapsed.value ? "1" : "0");
  }
}

function onNavigate(key) {
  store.view = key;
  drawer.value = false;
}

function toggleTheme() {
  setTheme(store.theme === "dark" ? "light" : "dark");
}

function doRefresh() {
  refreshKey.value++;
  ElMessage.success("已刷新");
}

async function doLogout() {
  try {
    await ElMessageBox.confirm("确定要退出登录吗？", "退出登录", {
      type: "warning",
      confirmButtonText: "退出",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  logout();
  ElMessage.success("已退出登录");
}

const timeText = computed(() => {
  const d = now.value;
  const p = (x) => String(x).padStart(2, "0");
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
});
const dateText = computed(() => {
  const d = now.value;
  const wd = ["日", "一", "二", "三", "四", "五", "六"][d.getDay()];
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 星期${wd}`;
});
</script>

<template>
  <el-container class="shell">
    <el-aside
      v-if="!isMobile"
      class="sidebar"
      :width="collapsed ? '64px' : '236px'"
    >
      <Sidebar :collapsed="collapsed" @navigate="onNavigate" />
    </el-aside>

    <el-container class="body">
      <el-header class="topbar">
        <div class="tb-left">
          <el-button
            circle
            text
            :icon="isMobile || collapsed ? Expand : Fold"
            title="切换侧边栏"
            @click="toggleSidebar"
          />
          <h2 class="page-title">{{ viewTitle() }}</h2>
        </div>
        <div class="tb-right">
          <div class="clock">
            <div class="date">{{ dateText }}</div>
            <div class="time">{{ timeText }}</div>
          </div>
          <el-button circle text :icon="Refresh" title="刷新当前页" @click="doRefresh" />
          <el-button
            circle
            text
            :icon="store.theme === 'dark' ? Sunny : Moon"
            :title="store.theme === 'dark' ? '切换浅色' : '切换深色'"
            @click="toggleTheme"
          />
          <el-button circle text :icon="SwitchButton" title="退出登录" @click="doLogout" />
        </div>
      </el-header>

      <el-main class="main">
        <transition name="view" mode="out-in">
          <component
            :is="views[store.view]"
            :key="store.view + '-' + refreshKey"
          />
        </transition>
      </el-main>
    </el-container>
  </el-container>

  <el-drawer
    v-model="drawer"
    direction="ltr"
    size="236px"
    :with-header="false"
    class="side-drawer"
  >
    <Sidebar :collapsed="false" @navigate="onNavigate" />
  </el-drawer>
</template>
