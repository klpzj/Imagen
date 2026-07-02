<script setup lang="ts">
import { computed, ref } from "vue";
import {
  Clipboard,
  Download,
  ExternalLink,
  LoaderCircle,
  RotateCcw
} from "@lucide/vue";
import { resolveAssetUrl } from "../api/client";
import { useImageStore } from "../stores/imageStore";

const emit = defineEmits<{
  "reuse-prompt": [prompt: string];
}>();

const imageStore = useImageStore();
const copied = ref(false);

const image = computed(() => imageStore.selectedImage ?? imageStore.latestImage);
const imageUrl = computed(() => (image.value ? resolveAssetUrl(image.value.url) : ""));
const createdAt = computed(() => {
  if (!image.value) {
    return "";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(image.value.created_at));
});

async function copyPrompt() {
  if (!image.value) {
    return;
  }

  await navigator.clipboard.writeText(image.value.prompt);
  copied.value = true;
  window.setTimeout(() => {
    copied.value = false;
  }, 1400);
}

function openImage() {
  if (imageUrl.value) {
    window.open(imageUrl.value, "_blank", "noopener");
  }
}
</script>

<template>
  <section aria-labelledby="preview-title">
    <div class="panel-header">
      <div>
        <h2 id="preview-title">Preview</h2>
        <p>{{ image ? image.filename : "No image selected" }}</p>
      </div>
    </div>

    <div class="preview-stage">
      <div v-if="imageStore.isGenerating" class="preview-loading">
        <LoaderCircle :size="34" aria-hidden="true" />
        <span>Generating image</span>
      </div>
      <img v-else-if="image" :src="imageUrl" :alt="image.prompt" />
      <div v-else class="empty-state">
        <strong>No generated images yet</strong>
        <span>Enter a prompt and generate to preview the result here.</span>
      </div>
    </div>

    <div v-if="image" class="preview-details">
      <div class="preview-actions" aria-label="Image actions">
        <a class="icon-button" :href="imageUrl" :download="image.filename" title="Download">
          <Download :size="17" aria-hidden="true" />
          <span>Download</span>
        </a>
        <button class="icon-button" type="button" title="Copy prompt" @click="copyPrompt">
          <Clipboard :size="17" aria-hidden="true" />
          <span>{{ copied ? "Copied" : "Copy" }}</span>
        </button>
        <button
          class="icon-button"
          type="button"
          title="Reuse prompt"
          @click="emit('reuse-prompt', image.prompt)"
        >
          <RotateCcw :size="17" aria-hidden="true" />
          <span>Reuse</span>
        </button>
        <button class="icon-button" type="button" title="Open image" @click="openImage">
          <ExternalLink :size="17" aria-hidden="true" />
          <span>Open</span>
        </button>
      </div>

      <dl class="metadata-grid">
        <div>
          <dt>Prompt</dt>
          <dd>{{ image.prompt }}</dd>
        </div>
        <div>
          <dt>Model</dt>
          <dd>{{ image.model }}</dd>
        </div>
        <div>
          <dt>Size</dt>
          <dd>{{ image.size }}</dd>
        </div>
        <div>
          <dt>Quality</dt>
          <dd>{{ image.quality }}</dd>
        </div>
        <div>
          <dt>Format</dt>
          <dd>{{ image.format }}</dd>
        </div>
        <div>
          <dt>Created</dt>
          <dd>{{ createdAt }}</dd>
        </div>
      </dl>
    </div>
  </section>
</template>
