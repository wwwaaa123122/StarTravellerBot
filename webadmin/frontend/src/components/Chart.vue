<script setup>
import * as echarts from "echarts";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
  option: { type: Object, required: true },
  height: { type: String, default: "300px" },
});

const el = ref(null);
let chart = null;
let ro = null;

onMounted(() => {
  chart = echarts.init(el.value);
  chart.setOption(props.option);
  ro = new ResizeObserver(() => chart && chart.resize());
  ro.observe(el.value);
});

watch(
  () => props.option,
  (opt) => {
    if (chart) chart.setOption(opt, true);
  },
  { deep: true }
);

onBeforeUnmount(() => {
  if (ro) ro.disconnect();
  if (chart) {
    chart.dispose();
    chart = null;
  }
});
</script>

<template>
  <div ref="el" class="chart" :style="{ height }"></div>
</template>
