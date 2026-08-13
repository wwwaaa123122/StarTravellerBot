<script setup>
import Icon from "../Icon.vue";

const props = defineProps({
  modelValue: { type: [Number, String], default: 0 },
  min: { type: Number, default: -Infinity },
  max: { type: Number, default: Infinity },
  step: { type: Number, default: 1 },
  precision: { type: Number, default: 0 },
});
const emit = defineEmits(["update:modelValue"]);

function clamp(v) {
  if (Number.isNaN(v)) return props.min;
  return Math.min(props.max, Math.max(props.min, v));
}
function stepTo(val) {
  emit("update:modelValue", clamp(val));
}
function onInput(e) {
  const v = parseFloat(e.target.value);
  emit("update:modelValue", Number.isNaN(v) ? "" : v);
}
function onBlur(e) {
  const v = parseFloat(e.target.value);
  emit("update:modelValue", clamp(Number.isNaN(v) ? props.min : v));
}
</script>

<template>
  <div class="ui-num">
    <button type="button" class="step" :disabled="Number(modelValue) <= min" @click="stepTo(Number(modelValue) - step)">
      <Icon name="close" :size="12" class="minus" />
    </button>
    <input
      type="number"
      :value="modelValue"
      :step="step"
      :min="min"
      :max="max"
      @input="onInput"
      @blur="onBlur"
    />
    <button type="button" class="step" :disabled="Number(modelValue) >= max" @click="stepTo(Number(modelValue) + step)">
      <Icon name="plus" :size="12" />
    </button>
  </div>
</template>

<style scoped>
.ui-num {
  display: flex;
  align-items: center;
  border: 1px solid var(--line-strong);
  border-radius: 9px;
  background: var(--surface);
  overflow: hidden;
}
.ui-num:focus-within {
  border-color: var(--vermilion);
  box-shadow: 0 0 0 3px rgba(192, 57, 43, 0.12);
}
.ui-num input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 13.5px;
  text-align: center;
  padding: 8px 4px;
  -moz-appearance: textfield;
}
.ui-num input::-webkit-outer-spin-button,
.ui-num input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.step {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 34px;
  border: none;
  background: var(--paper-deep);
  color: var(--ink-2);
  cursor: pointer;
}
.step:hover:not(:disabled) { background: #e4ddca; color: var(--ink); }
.step:disabled { opacity: 0.4; cursor: not-allowed; }
.minus { transform: rotate(45deg); }
</style>
