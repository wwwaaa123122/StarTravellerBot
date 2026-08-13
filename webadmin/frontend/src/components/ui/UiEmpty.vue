<script setup>
import Icon from "../Icon.vue";
defineProps({
  text: { type: String, default: "暂无数据" },
  icon: { type: String, default: "info" },
});
</script>

<template>
  <div class="ui-empty">
    <div class="empty-circle"><Icon :name="icon" :size="20" /></div>
    <p>{{ text }}</p>
  </div>
</template>

<style scoped>
.ui-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 36px 0;
  color: var(--ink-3);
}
.empty-circle {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--paper-deep);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}
.ui-empty p { margin: 0; font-size: 13px; letter-spacing: 0.5px; }
</style>
