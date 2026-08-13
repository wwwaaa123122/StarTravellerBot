<script setup>
import Icon from "../Icon.vue";

defineProps({
  variant: { type: String, default: "primary" }, // primary | soft | ghost | danger | text
  size: { type: String, default: "md" },         // sm | md | lg
  loading: Boolean,
  disabled: Boolean,
  icon: String,
  full: Boolean,
  danger: Boolean,
});
defineEmits(["click"]);
</script>

<template>
  <button
    class="ui-btn"
    :class="[variant, size, { full, loading }]"
    :disabled="disabled || loading"
    @click="$emit('click', $event)"
  >
    <span v-if="loading" class="spin" aria-hidden="true"></span>
    <Icon v-else-if="icon" :name="icon" :size="size === 'sm' ? 14 : 16" />
    <span v-if="$slots.default" class="txt"><slot /></span>
  </button>
</template>

<style scoped>
.ui-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 1px solid transparent;
  border-radius: 9px;
  font-family: var(--font-sans);
  font-weight: 500;
  letter-spacing: 0.5px;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease, transform 0.1s ease, box-shadow 0.15s ease;
  white-space: nowrap;
}
.ui-btn:active:not(:disabled) { transform: translateY(1px); }
.ui-btn:disabled { opacity: 0.55; cursor: not-allowed; }

.md { padding: 8px 18px; font-size: 13.5px; }
.sm { padding: 5px 12px; font-size: 12.5px; border-radius: 8px; }
.lg { padding: 11px 26px; font-size: 15px; border-radius: 10px; }
.full { width: 100%; }

.spin {
  width: 14px; height: 14px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: ui-spin 0.7s linear infinite;
}
@keyframes ui-spin { to { transform: rotate(360deg); } }

/* 朱色主操作 */
.primary { background: var(--vermilion); color: #fff; }
.primary:hover:not(:disabled) { background: var(--vermilion-dark); box-shadow: 0 4px 14px rgba(192, 57, 43, 0.3); }
.danger { background: var(--danger); color: #fff; }
.danger:hover:not(:disabled) { filter: brightness(0.92); }

/* 浅色软按钮 */
.soft { background: var(--paper-deep); color: var(--ink); border-color: transparent; }
.soft:hover:not(:disabled) { background: #e6dfce; }
.soft.danger { background: rgba(183, 40, 46, 0.1); color: var(--danger); }
.soft.danger:hover:not(:disabled) { background: rgba(183, 40, 46, 0.18); }

/* 描边 */
.ghost { background: var(--surface); color: var(--ink); border-color: var(--line-strong); }
.ghost:hover:not(:disabled) { border-color: var(--ink-3); background: var(--paper); }

/* 纯文字 */
.text { background: transparent; color: var(--indigo); padding: 4px 8px; }
.text:hover:not(:disabled) { background: var(--paper-deep); }
.text.danger { color: var(--danger); }
</style>
