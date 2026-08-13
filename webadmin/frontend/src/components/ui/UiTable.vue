<script setup>
import { computed, ref } from "vue";
import UiEmpty from "./UiEmpty.vue";
import UiSkeleton from "./UiSkeleton.vue";

const props = defineProps({
  columns: { type: Array, required: true }, // [{key,label,width,sortable,align}]
  data: { type: Array, default: () => [] },
  loading: Boolean,
  emptyText: { type: String, default: "暂无数据" },
  defaultSort: { type: Object, default: null }, // {key, order:'asc'|'desc'}
});

const sort = ref(props.defaultSort ? { ...props.defaultSort } : null);

function cmp(a, b) {
  const na = Number(a);
  const nb = Number(b);
  if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb;
  return String(a ?? "").localeCompare(String(b ?? ""), "zh-CN");
}

const sortedData = computed(() => {
  if (!sort.value) return props.data;
  const { key, order } = sort.value;
  const arr = [...props.data];
  arr.sort((x, y) => {
    const r = cmp(x[key], y[key]);
    return order === "asc" ? r : -r;
  });
  return arr;
});

function toggleSort(col) {
  if (!col.sortable) return;
  if (sort.value && sort.value.key === col.key) {
    sort.value = sort.value.order === "asc" ? { key: col.key, order: "desc" } : null;
  } else {
    sort.value = { key: col.key, order: "asc" };
  }
}
</script>

<template>
  <div class="ui-table-wrap">
    <UiSkeleton v-if="loading" :rows="6" />
    <template v-else-if="data.length">
      <div class="table-scroll">
        <table class="ui-table">
          <thead>
            <tr>
              <th
                v-for="col in columns"
                :key="col.key"
                :class="{ sortable: col.sortable }"
                :style="{ width: col.width, textAlign: col.align || 'left' }"
                @click="toggleSort(col)"
              >
                {{ col.label }}
                <span v-if="sort && sort.key === col.key" class="sort-arrow">
                  {{ sort.order === "asc" ? "▲" : "▼" }}
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, ri) in sortedData" :key="ri">
              <td
                v-for="col in columns"
                :key="col.key"
                :style="{ textAlign: col.align || 'left' }"
              >
                <slot :name="'cell-' + col.key" :row="row" :index="ri">
                  {{ row[col.key] }}
                </slot>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
    <UiEmpty v-else :text="emptyText" />
  </div>
</template>

<style scoped>
.ui-table-wrap { width: 100%; }
.table-scroll { overflow-x: auto; }
</style>
