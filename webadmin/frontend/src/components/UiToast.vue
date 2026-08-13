<script setup>
import { toasts, dismiss } from "../ui/toast";
import Icon from "./Icon.vue";

const ICON = { success: "check", error: "alert", warning: "alert", info: "info" };
</script>

<template>
  <teleport to="body">
    <div class="toast-wrap">
      <transition-group name="toast">
        <div
          v-for="t in toasts"
          :key="t.id"
          class="toast"
          :class="t.type"
          @click="dismiss(t.id)"
        >
          <span class="toast-ic"><Icon :name="ICON[t.type]" :size="14" /></span>
          <span class="toast-msg">{{ t.message }}</span>
        </div>
      </transition-group>
    </div>
  </teleport>
</template>

<style scoped>
.toast-wrap {
  position: fixed;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
  pointer-events: none;
}
.toast {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 16px 9px 11px;
  border-radius: 999px;
  background: var(--surface);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-pop);
  font-size: 13px;
  color: var(--ink);
  cursor: pointer;
  pointer-events: auto;
  max-width: 78vw;
}
.toast-ic {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  flex-shrink: 0;
  color: #fff;
}
.success .toast-ic { background: var(--bamboo); }
.error .toast-ic { background: var(--danger); }
.warning .toast-ic { background: var(--yamabuki); }
.info .toast-ic { background: var(--indigo); }
.toast-msg { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.toast-enter-active, .toast-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(-10px); }
</style>
