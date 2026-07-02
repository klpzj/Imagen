<script setup lang="ts">
import { onMounted } from "vue";
import AppShell from "./components/AppShell.vue";
import ErrorToast from "./components/ErrorToast.vue";
import { useImageStore } from "./stores/imageStore";

const imageStore = useImageStore();

onMounted(async () => {
  await imageStore.loadConfig();
  await imageStore.loadHistory();
});
</script>

<template>
  <AppShell />
  <ErrorToast
    v-if="imageStore.error"
    :message="imageStore.error"
    @dismiss="imageStore.clearError"
  />
</template>
