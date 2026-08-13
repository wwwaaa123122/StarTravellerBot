<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { store, viewTitle, logout } from "../store";
import { toast } from "../ui/toast";
import { confirm } from "../ui/modal";
import Icon from "./Icon.vue";
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

function doRefresh() {
  refreshKey.value++;
  toast.success("已刷新");
}

async function doLogout() {
  const ok = await confirm({
    title: "退出登录",
    message: "确定要退出登录吗？",
    confirmText: "退出",
    danger: true,
  });
  if (!ok) return;
  logout();
  toast.success("已退出登录");
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
  <div class="shell">
    <aside v-if="!isMobile" class="sidebar" :class="{ collapsed }">
      <Sidebar :collapsed="collapsed" @navigate="onNavigate" />
    </aside>

    <div class="body">
      <header class="topbar">
        <div class="tb-left">
          <button class="icon-btn" :title="isMobile || collapsed ? '展开侧栏' : '收起侧栏'" @click="toggleSidebar">
            <Icon :name="isMobile || collapsed ? 'expand' : 'fold'" :size="19" />
          </button>
          <h2 class="page-title">{{ viewTitle() }}</h2>
        </div>
        <div class="tb-right">
          <div class="clock">
            <div class="date">{{ dateText }}</div>
            <div class="time">{{ timeText }}</div>
          </div>
          <button class="icon-btn" title="刷新当前页" @click="doRefresh">
            <Icon name="refresh" :size="18" />
          </button>
          <button class="icon-btn" title="退出登录" @click="doLogout">
            <Icon name="logout" :size="18" />
          </button>
        </div>
      </header>

      <main class="main">
        <transition name="view" mode="out-in">
          <component :is="views[store.view]" :key="store.view + '-' + refreshKey" />
        </transition>
      </main>
    </div>
  </div>

  <teleport to="body">
    <transition name="fade">
      <div v-if="drawer" class="drawer-mask" @click="drawer = false"></div>
    </transition>
    <transition name="slide">
      <div v-if="drawer" class="drawer">
        <Sidebar :collapsed="false" @navigate="onNavigate" />
      </div>
    </transition>
  </teleport>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.slide-enter-active, .slide-leave-active { transition: transform 0.22s ease; }
.slide-enter-from, .slide-leave-to { transform: translateX(-100%); }
</style>