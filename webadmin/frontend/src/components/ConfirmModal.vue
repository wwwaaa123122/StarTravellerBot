<script setup>
import { confirmState, settleConfirm } from "../ui/modal";
import UiButton from "./ui/UiButton.vue";
import UiModal from "./ui/UiModal.vue";
</script>

<template>
  <UiModal
    v-model="confirmState.visible"
    :title="confirmState.title"
    width="420"
    @update:model-value="(v) => !v && settleConfirm(false)"
  >
    <p class="confirm-msg">{{ confirmState.message }}</p>
    <template #footer>
      <UiButton variant="ghost" @click="settleConfirm(false)">{{ confirmState.cancelText }}</UiButton>
      <UiButton :variant="confirmState.danger ? 'danger' : 'primary'" @click="settleConfirm(true)">
        {{ confirmState.confirmText }}
      </UiButton>
    </template>
  </UiModal>
</template>

<style scoped>
.confirm-msg {
  margin: 0;
  font-size: 13.5px;
  line-height: 1.8;
  color: var(--ink-2);
  white-space: pre-wrap;
}
</style>
