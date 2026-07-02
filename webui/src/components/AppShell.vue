<script setup lang="ts">
import { computed, ref } from "vue";
import { ImageIcon } from "@lucide/vue";
import GeneratePanel from "./GeneratePanel.vue";
import HistoryGallery from "./HistoryGallery.vue";
import ImagePreview from "./ImagePreview.vue";
import { useImageStore } from "../stores/imageStore";

const imageStore = useImageStore();
const reuseRequest = ref<{ prompt: string; token: number } | null>(null);

const activeImage = computed(
  () => imageStore.selectedImage ?? imageStore.latestImage
);

const modelLabel = computed(() => {
  if (activeImage.value) {
    return activeImage.value.model;
  }

  return imageStore.config?.default_model ?? "Loading config";
});

function reusePrompt(prompt: string) {
  reuseRequest.value = {
    prompt,
    token: Date.now()
  };
}
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">
        <ImageIcon :size="20" aria-hidden="true" />
        <div>
          <h1>Imagen Workspace</h1>
          <p>Text-to-image generation</p>
        </div>
      </div>
      <div class="topbar-status">
        <span>{{ modelLabel }}</span>
        <strong>{{ imageStore.isBusy ? "Generating" : "Ready" }}</strong>
      </div>
    </header>

    <main class="workspace">
      <GeneratePanel class="left-panel" :reuse-request="reuseRequest" />
      <ImagePreview class="preview-panel" @reuse-prompt="reusePrompt" />
      <HistoryGallery class="history-panel" />
    </main>
  </div>
</template>
