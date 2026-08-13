<script setup>
import Icon from "../Icon.vue";

defineProps({
  tone: { type: String, default: "paper" }, // paper | red | navy | bamboo | gold
  closable: Boolean,
});
defineEmits(["close"]);
</script>

<template>
  <span class="ui-tag" :class="tone">
    <slot />
    <button v-if="closable" type="button" class="tag-close" aria-label="移除" @click.stop="$emit('close')">
      <Icon name="close" :size="11" />
    </button>
  </span>
</template>

<style scoped>
.ui-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 11px;
  border-radius: 999px;
  font-size: 12px;
  line-height: 1.6;
  letter-spacing: 0.3px;
  max-width: 100%;
  overflow: hidden;
  white-space: nowrap;
}
.paper { background: var(--paper-deep); color: var(--ink-2); }
.red { background: rgba(192, 57, 43, 0.1); color: var(--vermilion-dark); }
.navy { background: rgba(42, 58, 85, 0.09); color: var(--navy); }
.bamboo { background: rgba(78, 138, 108, 0.12); color: #3c6e54; }
.gold { background: rgba(217, 145, 47, 0.13); color: #a56b12; }
.tag-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: currentColor;
  opacity: 0.65;
  cursor: pointer;
  padding: 0;
}
.tag-close:hover { opacity: 1; }
</style>
