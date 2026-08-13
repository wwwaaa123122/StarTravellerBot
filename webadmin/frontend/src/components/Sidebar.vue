<script setup>
import { store } from "../store";
import Icon from "./Icon.vue";

defineProps({ collapsed: Boolean });
const emit = defineEmits(["navigate"]);

const menus = [
  { key: "dashboard", label: "总览", icon: "dashboard" },
  { key: "users", label: "用户管理", icon: "users" },
  { key: "memory", label: "记忆库", icon: "memory" },
  { key: "plugins", label: "插件管理", icon: "plugins" },
  { key: "permissions", label: "权限管理", icon: "lock" },
  { key: "schedule", label: "定时任务", icon: "clock" },
  { key: "ai-settings", label: "AI 设置", icon: "sparkles" },
  { key: "prompts", label: "Prompt 管理", icon: "prompt" },
  { key: "settings", label: "系统设置", icon: "settings" },
];

function onSelect(key) {
  emit("navigate", key);
}
</script>

<template>
  <div class="side-wrap">
    <div class="brand">
      <div class="seal" aria-hidden="true">旅</div>
      <div v-if="!collapsed" class="brand-text">
        <div class="name">星辰旅人</div>
        <div class="sub">StarTraveller</div>
      </div>
    </div>

    <nav class="side-menu">
      <button
        v-for="m in menus"
        :key="m.key"
        class="side-item"
        :class="{ active: store.view === m.key }"
        :title="collapsed ? m.label : ''"
        @click="onSelect(m.key)"
      >
        <span class="ic"><Icon :name="m.icon" :size="18" /></span>
        <span v-if="!collapsed" class="txt">{{ m.label }}</span>
      </button>
    </nav>

    <div class="side-foot">
      <span v-if="!collapsed" class="verse">星河<br>旅人</span>
    </div>
  </div>
</template>

<style scoped>
.side-wrap { height: 100%; display: flex; flex-direction: column; }
.brand-text { min-width: 0; }
</style>