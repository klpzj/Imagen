<script setup lang="ts">
import { computed } from "vue";
import { resolveAssetUrl } from "../api/client";
import { useImageStore } from "../stores/imageStore";

const imageStore = useImageStore();
const images = computed(() => imageStore.historyImages);

function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}
</script>

<template>
  <section aria-labelledby="history-title">
    <div class="panel-header">
      <div>
        <h2 id="history-title">History</h2>
        <p>{{ images.length }} generated {{ images.length === 1 ? "image" : "images" }}</p>
      </div>
    </div>

    <div v-if="images.length" class="history-list" role="list">
      <button
        v-for="image in images"
        :key="image.id"
        class="history-item"
        :class="{ selected: image.id === imageStore.selectedImageId }"
        type="button"
        role="listitem"
        @click="imageStore.selectImage(image.id)"
      >
        <img :src="resolveAssetUrl(image.url)" :alt="image.prompt" />
        <span class="history-copy">
          <strong>{{ image.prompt }}</strong>
          <small>{{ image.size }} · {{ image.quality }} · {{ formatTimestamp(image.created_at) }}</small>
        </span>
      </button>
    </div>

    <div v-else class="history-empty">
      Generated images will appear here.
    </div>
  </section>
</template>
