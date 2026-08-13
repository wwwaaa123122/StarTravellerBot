<script setup>
import { computed, onBeforeUnmount, ref } from "vue";
import Icon from "../Icon.vue";

const props = defineProps({
  modelValue: { type: [String, Number], default: "" },
  options: { type: Array, default: () => [] }, // string[] | {label,value}[]
  placeholder: { type: String, default: "请选择" },
  allowCreate: Boolean,
  disabled: Boolean,
});
const emit = defineEmits(["update:modelValue"]);

const open = ref(false);
const kw = ref("");
const root = ref(null);

const opts = computed(() =>
  props.options.map((o) => (typeof o === "object" && o !== null ? o : { label: String(o), value: o }))
);

const filtered = computed(() => {
  const q = kw.value.trim().toLowerCase();
  const list = q
    ? opts.value.filter((o) => String(o.label).toLowerCase().includes(q))
    : opts.value;
  const exists = opts.value.some((o) => String(o.value) === String(props.modelValue));
  if (props.allowCreate && q && !exists && !list.some((o) => String(o.label) === kw.value.trim())) {
    list.push({ label: kw.value.trim(), value: kw.value.trim() });
  }
  return list;
});

const display = computed(() => {
  const o = opts.value.find((x) => String(x.value) === String(props.modelValue));
  return o ? o.label : (props.modelValue ?? "");
});

function select(o) {
  emit("update:modelValue", o.value);
  open.value = false;
  kw.value = "";
}
function toggle() {
  if (props.disabled) return;
  open.value = !open.value;
  if (open.value) kw.value = "";
}
function onKey(e) {
  if (e.key === "Escape") open.value = false;
  if (e.key === "Enter" && filtered.value.length === 1) {
    select(filtered.value[0]);
  }
}
function onDocClick(e) {
  if (root.value && !root.value.contains(e.target)) open.value = false;
}
onBeforeUnmount(() => document.removeEventListener("mousedown", onDocClick));
function onMount() { document.addEventListener("mousedown", onDocClick); }
onMount();
</script>

<template>
  <div ref="root" class="ui-select" :class="{ open, disabled }">
    <button type="button" class="field" @click="toggle">
      <span class="field-txt" :class="{ placeholder: !modelValue && modelValue !== 0 }">
        {{ modelValue === "" || modelValue === null || modelValue === undefined ? placeholder : display }}
      </span>
      <Icon name="chevronDown" :size="15" class="arrow" />
    </button>

    <transition name="drop">
      <div v-if="open" class="drop">
        <div class="search" v-if="opts.length > 4 || allowCreate">
          <input
            v-model="kw"
            placeholder="搜索 / 输入新值"
            @keydown="onKey"
            @input="open = true"
          />
        </div>
        <div class="opt-list">
          <button
            v-for="o in filtered"
            :key="o.value"
            type="button"
            class="opt"
            :class="{ active: String(o.value) === String(modelValue), create: !opts.some((x) => x.value === o.value) }"
            @click="select(o)"
          >
            <span>{{ o.label }}</span>
            <Icon v-if="String(o.value) === String(modelValue)" name="check" :size="14" />
          </button>
          <div v-if="filtered.length === 0" class="no-data">无匹配项</div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.ui-select { position: relative; }
.field {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  padding: 9px 12px;
  border: 1px solid var(--line-strong);
  border-radius: 9px;
  background: var(--surface);
  color: var(--ink);
  font-size: 13.5px;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.ui-select.open .field {
  border-color: var(--vermilion);
  box-shadow: 0 0 0 3px rgba(192, 57, 43, 0.12);
}
.ui-select.disabled { opacity: 0.6; }
.field-txt { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.field-txt.placeholder { color: var(--ink-3); }
.arrow { color: var(--ink-3); transition: transform 0.18s ease; }
.ui-select.open .arrow { transform: rotate(180deg); }

.drop {
  position: absolute;
  top: calc(100% + 5px);
  left: 0;
  right: 0;
  z-index: 30;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 10px;
  box-shadow: var(--shadow-pop);
  overflow: hidden;
}
.search { padding: 8px; border-bottom: 1px solid var(--line); }
.search input {
  width: 100%;
  border: 1px solid var(--line-strong);
  border-radius: 7px;
  padding: 6px 10px;
  font-size: 13px;
  background: var(--surface-2);
  color: var(--ink);
  outline: none;
}
.search input:focus { border-color: var(--vermilion); }
.opt-list { max-height: 220px; overflow-y: auto; padding: 5px; }
.opt {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  padding: 8px 10px;
  border: none;
  border-radius: 7px;
  background: transparent;
  color: var(--ink);
  font-size: 13px;
  font-family: var(--font-sans);
  text-align: left;
  cursor: pointer;
}
.opt:hover { background: var(--paper-deep); }
.opt.active { color: var(--vermilion); font-weight: 600; }
.opt.create { color: var(--indigo); }
.opt.create::after { content: "＋ 新增"; font-size: 11px; color: var(--ink-3); }
.no-data { padding: 14px; text-align: center; font-size: 12.5px; color: var(--ink-3); }

.drop-enter-active, .drop-leave-active { transition: opacity 0.14s ease, transform 0.14s ease; }
.drop-enter-from, .drop-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
