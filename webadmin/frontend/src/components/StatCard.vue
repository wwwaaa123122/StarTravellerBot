<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  sub: { type: String, default: "" },
  dot: { type: String, default: "" }, // success | off | warn
});
</script>

<template>
  <div class="stat-card">
    <span v-if="dot" class="dot" :class="dot"></span>
    <div class="label">{{ label }}</div>
    <div class="value">{{ value }}</div>
    <div v-if="sub" class="sub">{{ sub }}</div>
  </div>
</template>