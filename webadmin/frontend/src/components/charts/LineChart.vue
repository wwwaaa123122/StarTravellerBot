<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

const props = defineProps({
  data: { type: Array, default: () => [] }, // [{label, value}]
  height: { type: Number, default: 260 },
  color: { type: String, default: "#2A3A55" },
  fill: { type: String, default: "#2A3A55" },
});

const wrap = ref(null);
const width = ref(0);
const hoverIdx = ref(null);
let ro = null;

onMounted(() => {
  width.value = wrap.value.clientWidth;
  ro = new ResizeObserver(() => { width.value = wrap.value.clientWidth; });
  ro.observe(wrap.value);
});
onBeforeUnmount(() => ro && ro.disconnect());

const PAD = { l: 36, r: 14, t: 16, b: 26 };

const points = computed(() => {
  const data = props.data;
  const w = width.value - PAD.l - PAD.r;
  const h = props.height - PAD.t - PAD.b;
  if (!data.length || w <= 0) return [];
  const maxV = Math.max(1, ...data.map((d) => Number(d.value) || 0));
  const step = w / (data.length - 1 || 1);
  return data.map((d, i) => ({
    x: PAD.l + i * step,
    y: PAD.t + h * (1 - (Number(d.value) || 0) / maxV),
    ...d,
  }));
});

const linePath = computed(() => {
  const pts = points.value.map((p) => [p.x, p.y]);
  if (pts.length < 2) return "";
  let d = `M ${pts[0][0]},${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[Math.min(pts.length - 1, i + 2)];
    const c1x = p1[0] + (p2[0] - p0[0]) / 6;
    const c1y = p1[1] + (p2[1] - p0[1]) / 6;
    const c2x = p2[0] - (p3[0] - p1[0]) / 6;
    const c2y = p2[1] - (p3[1] - p1[1]) / 6;
    d += ` C ${c1x},${c1y} ${c2x},${c2y} ${p2[0]},${p2[1]}`;
  }
  return d;
});

const areaPath = computed(() => {
  if (!linePath.value) return "";
  const pts = points.value;
  const base = PAD.t + (props.height - PAD.t - PAD.b);
  return `${linePath.value} L ${pts[pts.length - 1].x},${base} L ${pts[0].x},${base} Z`;
});

const yTicks = computed(() => {
  const maxV = Math.max(1, ...props.data.map((d) => Number(d.value) || 0));
  const nice = niceCeil(maxV, 3);
  return [0, 1, 2, 3].map((i) => ({
    v: (nice / 3) * i,
    y: PAD.t + (props.height - PAD.t - PAD.b) * (1 - i / 3),
  }));
});

function niceCeil(v, ticks) {
  const raw = v / ticks;
  const mag = Math.pow(10, Math.floor(Math.log10(Math.max(1, raw))));
  const norm = raw / mag;
  const nice = norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10;
  return nice * mag * ticks;
}

const xLabelStep = computed(() => {
  const n = points.value.length;
  if (n <= 8) return 1;
  return Math.ceil(n / 8);
});

function onMove(e) {
  const svg = e.currentTarget;
  const rect = svg.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const pts = points.value;
  if (!pts.length) return;
  let idx = 0;
  let dist = Infinity;
  pts.forEach((p, i) => {
    const d = Math.abs(p.x - x);
    if (d < dist) { dist = d; idx = i; }
  });
  hoverIdx.value = idx;
}
function onLeave() { hoverIdx.value = null; }

const tooltipStyle = computed(() => {
  const p = hoverIdx.value != null ? points.value[hoverIdx.value] : null;
  if (!p) return {};
  const w = width.value;
  return {
    left: (p.x + 10 > w - 120 ? p.x - 128 : p.x + 10) + "px",
    top: (p.y - 36) + "px",
  };
});
</script>

<template>
  <div ref="wrap" class="line-chart" :style="{ height: height + 'px' }">
    <svg
      v-if="points.length"
      :width="width"
      :height="height"
      @mousemove="onMove"
      @mouseleave="onLeave"
    >
      <defs>
        <linearGradient :id="'lg-' + (fill || color).replace(/[^a-zA-Z0-9]/g, '')" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" :stop-color="fill" stop-opacity="0.22" />
          <stop offset="100%" :stop-color="fill" stop-opacity="0" />
        </linearGradient>
      </defs>

      <g v-for="t in yTicks" :key="t.y">
        <line :x1="PAD.l" :x2="width - PAD.r" :y1="t.y" :y2="t.y" stroke="#e9e2d2" stroke-width="1" stroke-dasharray="3 4" />
        <text :x="PAD.l - 8" :y="t.y + 4" text-anchor="end" font-size="10" fill="#a59c8d">{{ Math.round(t.v) }}</text>
      </g>

      <path :d="areaPath" :fill="'url(#' + 'lg-' + (fill || color).replace(/[^a-zA-Z0-9]/g, '') + ')'" />
      <path :d="linePath" fill="none" :stroke="color" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" />

      <g v-for="(p, i) in points" :key="i">
        <line
          v-if="hoverIdx === i"
          :x1="p.x" :x2="p.x"
          :y1="PAD.t" :y2="height - PAD.b"
          stroke="#c0392b" stroke-width="1" stroke-dasharray="2 3" opacity="0.5"
        />
        <circle :cx="p.x" :cy="p.y" r="3.2" :fill="color" :stroke="hoverIdx === i ? '#fff' : 'none'" :stroke-width="hoverIdx === i ? 2 : 0" />
      </g>

      <g v-for="(p, i) in points" :key="'x' + i">
        <text
          v-if="i % xLabelStep === 0 || i === points.length - 1"
          :x="p.x" :y="height - 8"
          text-anchor="middle"
          font-size="10"
          fill="#a59c8d"
        >{{ p.label }}</text>
      </g>
    </svg>

    <transition name="tip">
      <div v-if="hoverIdx != null && points[hoverIdx]" class="chart-tip" :style="tooltipStyle">
        <span class="tip-label">{{ points[hoverIdx].label }}</span>
        <span class="tip-value">{{ points[hoverIdx].value }}</span>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.line-chart { position: relative; width: 100%; }
.line-chart svg { display: block; overflow: visible; }
.chart-tip {
  position: absolute;
  z-index: 5;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 7px 11px;
  border-radius: 8px;
  background: var(--surface);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-pop);
  pointer-events: none;
  font-size: 11px;
  white-space: nowrap;
}
.tip-label { color: var(--ink-3); }
.tip-value { font-weight: 700; color: var(--ink); font-variant-numeric: tabular-nums; }
.tip-enter-active, .tip-leave-active { transition: opacity 0.12s ease; }
.tip-enter-from, .tip-leave-to { opacity: 0; }
</style>
