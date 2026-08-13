<script setup>
import { computed, onBeforeUnmount, ref } from "vue";
import Icon from "../Icon.vue";
import UiTag from "./UiTag.vue";

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: "请选择" },
  allowCreate: Boolean,
  clearable: Boolean,
  noDataText: { type: String, default: "暂无数据" },
  disabled: Boolean,
});
const emit = defineEmits(["update:modelValue"]);

const open = ref(false);
const kw = ref("");
const inputEl = ref(null);
const root = ref(null);

const values = computed(() => (Array.isArray(props.modelValue) ? props.modelValue : []));
const selected = computed(() => new Set(values.value.map((v) => String(v))));
const opts = computed(() =>
  props.options.map((o) => (typeof o === "object" && o !== null ? o : { label: String(o), value: o }))
);

const filtered = computed(() => {
  const q = kw.value.trim().toLowerCase();
  const base = q ? opts.value.filter((o) => String(o.label).toLowerCase().includes(q)) : opts.value;
  const list = base.filter((o) => !selected.value.has(String(o.value)));
  const exactInList = list.some((o) => String(o.label) === kw.value.trim());
  if (props.allowCreate && q && !exactInList) {
    list.push({ label: kw.value.trim(), value: kw.value.trim(), create: true });
  }
  return list;
});

function toggle() {
  if (props.disabled) return;
  open.value = !open.value;
  if (open.value) setTimeout(() => inputEl.value && inputEl.value.focus(), 0);
}
function add(val) {
  const s = String(val).trim();
  if (!s || selected.value.has(s)) return;
  emit("update:modelValue", [...values.value, s]);
  kw.value = "";
}
function remove(val) {
  emit("update:modelValue", values.value.filter((v) => String(v) !== String(val)));
}
function clearAll() {
  emit("update:modelValue", []);
}
function onInput() { open.value = true; }
function onKey(e) {
  if (e.key === "Escape") { open.value = false; e.target.blur(); }
  if (e.key === "Enter") {
    e.preventDefault();
    if (filtered.value.length) {
      const hit = filtered.value.find((o) => String(o.label) === kw.value.trim()) || filtered.value[0];
      add(hit.value);
    }
  }
  if (e.key === "Backspace" && !kw.value && values.value.length) {
    emit("update:modelValue", values.value.slice(0, -1));
  }
}
function onDocClick(e) {
  if (root.value && !root.value.contains(e.target)) open.value = false;
}
onBeforeUnmount(() => document.removeEventListener("mousedown", onDocClick));
document.addEventListener("mousedown", onDocClick);
</script>

<template>
  <div ref="root" class="ui-mselect" :class="{ open, disabled }">
    <div class="field" @click="toggle">
      <div class="chips">
        <UiTag v-for="v in values" :key="v" tone="navy" closable @close="remove(v)">{{ v }}</UiTag>
        <input
          ref="inputEl"
          v-model="kw"
          class="ms-input"
          :placeholder="values.length ? '' : placeholder"
          @input="onInput"
          @keydown="onKey"
          @click.stop
        />
      </div>
      <div class="field-icons">
        <button v-if="clearable && values.length" type="button" class="clear" @click.stop="clearAll" aria-label="清空">
          <Icon name="close" :size="13" />
        </button>
        <Icon name="chevronDown" :size="15" class="arrow" />
      </div>
    </div>

    <transition name="drop">
      <div v-if="open" class="drop">
        <div class="opt-list">
          <button
            v-for="o in filtered"
            :key="o.value"
            type="button"
            class="opt"
            :class="{ create: o.create }"
            @click="add(o.value)"
          >
            <span>{{ o.label }}</span>
            <Icon name="plus" :size="13" />
          </button>
          <div v-if="filtered.length === 0" class="no-data">
            {{ noDataText }}
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.ui-mselect { position: relative; }
.field {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  min-height: 40px;
  padding: 5px 10px;
  border: 1px solid var(--line-strong);
  border-radius: 9px;
  background: var(--surface);
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.ui-mselect.open .field {
  border-color: var(--vermilion);
  box-shadow: 0 0 0 3px rgba(192, 57, 43, 0.12);
}
.ui-mselect.disabled { opacity: 0.6; }
.chips { display: flex; flex-wrap: wrap; gap: 5px; align-items: center; flex: 1; min-width: 0; }
.ms-input {
  flex: 1;
  min-width: 90px;
  border: none;
  outline: none;
  background: transparent;
  color: var(--ink);
  font-size: 13px;
  font-family: var(--font-sans);
  padding: 4px 2px;
}
.ms-input::placeholder { color: var(--ink-3); }
.field-icons { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.clear {
  display: inline-flex;
  border: none;
  background: transparent;
  color: var(--ink-3);
  cursor: pointer;
  padding: 2px;
}
.clear:hover { color: var(--danger); }
.arrow { color: var(--ink-3); transition: transform 0.18s ease; }
.ui-mselect.open .arrow { transform: rotate(180deg); }

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
.opt.create { color: var(--indigo); }
.opt.create::after { content: "＋ 回车新增"; font-size: 11px; color: var(--ink-3); }
.no-data { padding: 14px; text-align: center; font-size: 12.5px; color: var(--ink-3); }

.drop-enter-active, .drop-leave-active { transition: opacity 0.14s ease, transform 0.14s ease; }
.drop-enter-from, .drop-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
