<script setup>
defineProps({
  rows: { type: Number, default: 4 },
  height: { type: [Number, String], default: 14 },
});
</script>

<template>
  <div class="ui-skeleton" :style="{ '--sk-h': typeof height === 'number' ? height + 'px' : height }">
    <span v-for="i in rows" :key="i" class="sk-block" :style="{ width: (100 - ((i * 13) % 34)) + '%' }"></span>
  </div>
</template>

<style scoped>
.ui-skeleton { display: flex; flex-direction: column; gap: 12px; padding: 4px 0; }
.sk-block {
  height: var(--sk-h);
  border-radius: 6px;
  background: linear-gradient(90deg, var(--paper-deep) 25%, #ece5d5 40%, var(--paper-deep) 60%);
  background-size: 200% 100%;
  animation: sk-shimmer 1.3s ease-in-out infinite;
}
@keyframes sk-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
