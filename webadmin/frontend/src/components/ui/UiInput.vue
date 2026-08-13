<script setup>
import { ref } from "vue";
import Icon from "../Icon.vue";

const props = defineProps({
  modelValue: { type: [String, Number], default: "" },
  type: { type: String, default: "text" },
  placeholder: String,
  size: { type: String, default: "md" },
  maxlength: [Number, String],
  disabled: Boolean,
  showPassword: Boolean,
  prefixIcon: String,
});
const emit = defineEmits(["update:modelValue", "enter"]);
const showPwd = ref(false);

function onInput(e) {
  emit("update:modelValue", e.target.value);
}
function onKey(e) {
  if (e.key === "Enter") emit("enter");
}
</script>

<template>
  <div class="ui-input" :class="[size, { 'with-prefix': prefixIcon, disabled }]">
    <Icon v-if="prefixIcon" :name="prefixIcon" :size="16" class="pre-icon" />
    <input
      :type="showPassword ? (showPwd ? 'text' : 'password') : type"
      :value="modelValue"
      :placeholder="placeholder"
      :maxlength="maxlength"
      :disabled="disabled"
      @input="onInput"
      @keydown="onKey"
    />
    <button
      v-if="showPassword"
      type="button"
      class="pwd-toggle"
      :title="showPwd ? '隐藏密码' : '显示密码'"
      @click="showPwd = !showPwd"
    >
      <Icon :name="showPwd ? 'eyeOff' : 'eye'" :size="16" />
    </button>
  </div>
</template>

<style scoped>
.ui-input {
  display: flex;
  align-items: center;
  background: var(--surface);
  border: 1px solid var(--line-strong);
  border-radius: 9px;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.ui-input:focus-within {
  border-color: var(--vermilion);
  box-shadow: 0 0 0 3px rgba(192, 57, 43, 0.12);
}
.ui-input.disabled { opacity: 0.6; }
.ui-input input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 13.5px;
  padding: 9px 12px;
}
.md input { padding: 9px 12px; }
.sm input { padding: 6px 10px; font-size: 13px; }
.lg input { padding: 11px 14px; font-size: 14.5px; }
.ui-input input::placeholder { color: var(--ink-3); }
.with-prefix input { padding-left: 6px; }
.pre-icon { margin-left: 11px; color: var(--ink-3); flex-shrink: 0; }
.pwd-toggle {
  display: inline-flex;
  align-items: center;
  border: none;
  background: transparent;
  color: var(--ink-3);
  cursor: pointer;
  padding: 0 10px;
}
.pwd-toggle:hover { color: var(--ink-2); }
</style>
