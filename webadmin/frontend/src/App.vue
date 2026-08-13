<script setup>
import { store } from "./store";
import LoginView from "./components/LoginView.vue";
import AppLayout from "./components/AppLayout.vue";
import UiToast from "./components/UiToast.vue";
import ConfirmModal from "./components/ConfirmModal.vue";
</script>

<template>
  <LoginView v-if="!store.authenticated" />
  <AppLayout v-else />
  <UiToast />
  <ConfirmModal />
</template>