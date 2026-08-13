<script setup>
const props = defineProps({
  modelValue: Boolean,
  disabled: Boolean,
  loading: Boolean,
  activeText: String,
  inactiveText: String,
  size: { type: String, default: "md" },
});
const emit = defineEmits(["update:modelValue", "change"]);

function toggle() {
  if (props.disabled || props.loading) return;
  emit("update:modelValue", !props.modelValue);
  emit("change", !props.modelValue);
}
</script>

<template>
  <div class="ui-switch" :class="size">
    <button
      type="button"
      class="track"
      :class="{ on: modelValue, disabled: disabled || loading }"
      role="switch"
      :aria-checked="modelValue"
      :disabled="disabled || loading"
      @click="toggle"
    >
      <span class="knob"><i v-if="loading" class="mini-spin"></i></span>
    </button>
    <span v-if="activeText || inactiveText" class="label" :class="{ on: modelValue }">
      {{ modelValue ? activeText : inactiveText }}
    </span>
  </div>
</template>

<style scoped>
.ui-switch { display: inline-flex; align-items: center; gap: 9px; }
.track {
  position: relative;
  width: 44px;
  height: 24px;
  border-radius: 999px;
  border: none;
  background: #d5cdbc;
  cursor: pointer;
  transition: background 0.2s ease;
  flex-shrink: 0;
  padding: 0;
}
.track.on { background: var(--bamboo); }
.track.on:hover { background: #417758; }
.track:hover { background: #c9c0ad; }
.track.disabled { opacity: 0.55; cursor: not-allowed; }
.knob {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s ease;
}
.track.on .knob { transform: translateX(20px); }
.lg.track, .lg .track { width: 50px; height: 28px; }
.lg .knob { width: 24px; height: 24px; }
.lg.track.on .knob, .lg .track.on .knob { transform: translateX(22px); }
.sm.track, .sm .track { width: 36px; height: 20px; }
.sm .knob { width: 16px; height: 16px; }
.sm.track.on .knob, .sm .track.on .knob { transform: translateX(16px); }

.label { font-size: 13px; color: var(--ink-3); transition: color 0.2s ease; }
.label.on { color: var(--bamboo); }

.mini-spin {
  width: 10px; height: 10px;
  border: 1.5px solid var(--bamboo);
  border-top-color: transparent;
  border-radius: 50%;
  animation: sw-spin 0.6s linear infinite;
}
@keyframes sw-spin { to { transform: rotate(360deg); } }
</style>
