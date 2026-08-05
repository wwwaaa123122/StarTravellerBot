<script setup>
import { Odometer, User, Collection, Grid, AlarmClock, Setting, SwitchButton } from "@element-plus/icons-vue";
import { store, logout } from "../store";

defineProps({ collapsed: Boolean });
const emit = defineEmits(["navigate"]);

const menus = [
  { key: "dashboard", label: "仪表盘", icon: Odometer },
  { key: "users", label: "用户管理", icon: User },
  { key: "memory", label: "记忆库", icon: Collection },
  { key: "plugins", label: "插件管理", icon: Grid },
  { key: "schedule", label: "定时任务", icon: AlarmClock },
  { key: "settings", label: "系统设置", icon: Setting },
];

function onSelect(key) {
  emit("navigate", key);
}
</script>

<template>
  <div class="side-wrap">
    <div class="brand">
      <div class="logo">星</div>
      <div v-show="!collapsed" class="brand-text">
        <div class="name">StarTraveller</div>
        <div class="sub">星辰旅人 · 管理后台</div>
      </div>
    </div>

    <el-menu
      class="side-menu"
      :default-active="store.view"
      :collapse="collapsed"
      :collapse-transition="false"
      @select="onSelect"
    >
      <el-menu-item v-for="m in menus" :key="m.key" :index="m.key">
        <el-icon><component :is="m.icon" /></el-icon>
        <template #title>{{ m.label }}</template>
      </el-menu-item>
    </el-menu>

    <div v-show="!collapsed" class="side-foot">
      <el-button text type="danger" :icon="SwitchButton" @click="logout">退出登录</el-button>
    </div>
  </div>
</template>
