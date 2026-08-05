<script setup>
import { store } from "./store";
import LoginView from "./components/LoginView.vue";
import AppLayout from "./components/AppLayout.vue";
</script>

<template>
  <LoginView v-if="!store.authenticated" />
  <AppLayout v-else />
</template>
