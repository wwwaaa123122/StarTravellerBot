<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

const props = defineProps({
  data: { type: Array, default: () => [] }, // [{name, value}]
  height: { type: Number, default: 260 },
});

const PALETTE = ["#2A3A55", "#C0392B", "#4E8A6C", "#D9912F", "#3D5A80", "#8C6E9E", "#D98C8C", "#6E8B74", "#B7A261"];
const hover = ref(null);

const total = computed(() => props.data.reduce((s, d) => s + (Number(d.value) || 0), 0));

const segments = computed(() => {
  let acc = 0;
  return props.data.map((d, i) => {
    const v = Number(d.value) || 0;
    const frac = total.value ? v / total.value : 0;
    const seg = { ...d, frac, color: PALETTE[i % PALETTE.length] };
    acc += frac;
    seg.dashoffset = -acc;
    return seg;
  });
});

const R = 62;
const C = 2 * Math.PI * R;
const center = computed(() => {
  if (hover.value != null && props.data[hover.value]) {
    const d = props.data[hover.value];
    return { name: d.name, value: d.value, frac: total.value ? (d.value / total.value) : 0 };
  }
  return { name: null, value: total.value, frac: 1 };
});

function renderValue(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
  if (n >= 1000) return (n / 1000).toFixed(1) + "K";
  return String(n);
}
</script>

<template>
  <div class="donut" :style="{ height: height + 'px' }">
    <div v-if="total > 0" class="donut-main">
      <svg :width="height" :height="height" viewBox="0 0 160 160">
        <circle cx="80" cy="80" :r="R" fill="none" stroke="#efeadd" stroke-width="20" />
        <circle
          v-for="(s, i) in segments"
          :key="i"
          cx="80"
          cy="80"
          :r="R"
          fill="none"
          :stroke="s.color"
          stroke-width="20"
          stroke-linecap="butt"
          :stroke-dasharray="(Math.max(s.frac * C - 2, 0)) + ' ' + C"
          :stroke-dashoffset="s.dashoffset * C"
          transform="rotate(-90 80 80)"
          class="seg"
          :class="{ dim: hover != null && hover !== i }"
          @mouseenter="hover = i"
          @mouseleave="hover = null"
        />
      </svg>
      <div class="donut-center">
        <span v-if="center.name" class="c-name">{{ center.name }}</span>
        <span class="c-value">{{ renderValue(center.value) }}</span>
        <span v-if="center.name" class="c-frac">{{ Math.round(center.frac * 100) }}%</span>
        <span v-else class="c-frac">总计</span>
      </div>
    </div>
    <div v-else class="donut-empty">暂无数据</div>

    <div class="legend">
      <div
        v-for="(s, i) in segments"
        :key="i"
        class="legend-item"
        :class="{ active: hover === i }"
        @mouseenter="hover = i"
        @mouseleave="hover = null"
      >
        <span class="swatch" :style="{ background: s.color }"></span>
        <span class="l-name">{{ s.name }}</span>
        <span class="l-val">{{ renderValue(s.value) }} · {{ Math.round(s.frac * 100) }}%</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.donut {
  display: flex;
  align-items: center;
  gap: 18px;
  width: 100%;
}
.donut-main { position: relative; flex-shrink: 0; }
.donut-main svg { display: block; }
.seg { cursor: pointer; transition: opacity 0.15s ease; }
.seg.dim { opacity: 0.35; }
.donut-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}
.c-name { font-size: 11px; color: var(--ink-3); max-width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.c-value { font-size: 20px; font-weight: 700; font-family: var(--font-serif); font-variant-numeric: tabular-nums; }
.c-frac { font-size: 10.5px; color: var(--ink-3); }

.legend { display: flex; flex-direction: column; gap: 7px; flex: 1; min-width: 0; max-height: 100%; overflow-y: auto; }
.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--ink-2);
  padding: 4px 8px;
  border-radius: 7px;
  cursor: pointer;
  transition: background 0.12s ease;
}
.legend-item:hover, .legend-item.active { background: var(--paper-deep); }
.swatch { width: 9px; height: 9px; border-radius: 3px; flex-shrink: 0; }
.l-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.l-val { margin-left: auto; color: var(--ink-3); font-variant-numeric: tabular-nums; flex-shrink: 0; }
.donut-empty { color: var(--ink-3); font-size: 13px; }
</style>
