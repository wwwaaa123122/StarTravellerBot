<script setup>
import { watch } from "vue";
import Icon from "../Icon.vue";

const props = defineProps({
  modelValue: Boolean,
  title: { type: String, default: "" },
  width: { type: [Number, String], default: 520 },
});
const emit = defineEmits(["update:modelValue", "close"]);

watch(
  () => props.modelValue,
  (v) => {
    if (v) {
      document.addEventListener("keydown", onKey);
    } else {
      document.removeEventListener("keydown", onKey);
    }
  }
);
function onKey(e) {
  if (e.key === "Escape") close();
}
function close() {
  emit("update:modelValue", false);
  emit("close");
}
function onMask(e) {
  if (e.target === e.currentTarget) close();
}
</script>

<template>
  <teleport to="body">
    <transition name="modal">
      <div v-if="modelValue" class="modal-mask" @mousedown.self="onMask">
        <div class="modal-card" :style="{ width: typeof width === 'number' ? width + 'px' : width }">
          <div class="modal-head">
            <h3>{{ title }}</h3>
            <button type="button" class="modal-close" @click="close" aria-label="关闭">
              <Icon name="close" :size="16" />
            </button>
          </div>
          <div class="modal-body"><slot /></div>
          <div v-if="$slots.footer" class="modal-foot"><slot name="footer" /></div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 60;
  background: rgba(47, 43, 37, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.modal-card {
  background: var(--surface);
  border-radius: 14px;
  box-shadow: 0 18px 60px rgba(30, 24, 14, 0.3);
  max-width: 100%;
  max-height: 86vh;
  display: flex;
  flex-direction: column;
}
.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px 0;
}
.modal-head h3 {
  margin: 0;
  font-family: var(--font-serif);
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
.modal-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: var(--ink-3);
  cursor: pointer;
}
.modal-close:hover { background: var(--paper-deep); color: var(--ink); }
.modal-body { padding: 16px 20px 20px; overflow-y: auto; }
.modal-foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 0 20px 18px;
}

.modal-enter-active, .modal-leave-active { transition: opacity 0.18s ease; }
.modal-enter-active .modal-card, .modal-leave-active .modal-card { transition: transform 0.18s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .modal-card, .modal-leave-to .modal-card { transform: translateY(12px) scale(0.98); }
</style>