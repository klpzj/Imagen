<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Eraser, Sparkles } from "@lucide/vue";
import ParameterControls from "./ParameterControls.vue";
import { useImageStore } from "../stores/imageStore";
import type { ImageOptions } from "../types/image";

const props = defineProps<{
  reuseRequest: { prompt: string; token: number } | null;
}>();

const imageStore = useImageStore();
const prompt = ref("");
const options = ref<ImageOptions>({
  model: undefined,
  size: "1024x1024",
  quality: "auto",
  output_format: "png",
  background: "auto",
  n: 1
});

const canGenerate = computed(
  () => prompt.value.trim().length > 0 && !imageStore.isGenerating
);

watch(
  () => imageStore.config,
  (config) => {
    if (!config) {
      return;
    }

    options.value = {
      model: options.value.model ?? config.default_model ?? config.models[0],
      size: config.sizes.includes(options.value.size)
        ? options.value.size
        : config.sizes[0],
      quality: config.qualities.includes(options.value.quality)
        ? options.value.quality
        : config.qualities[0],
      output_format: config.formats.includes(options.value.output_format)
        ? options.value.output_format
        : config.formats[0],
      background: config.backgrounds.includes(options.value.background ?? "")
        ? options.value.background
        : config.backgrounds[0],
      n: clampCount(options.value.n, config.max_n)
    };
  },
  { immediate: true }
);

watch(
  () => props.reuseRequest,
  (request) => {
    if (request) {
      prompt.value = request.prompt;
    }
  }
);

function clampCount(value: number, max: number): number {
  return Math.max(1, Math.min(max, Math.round(value || 1)));
}

async function submit() {
  if (!canGenerate.value) {
    return;
  }

  const maxN = imageStore.config?.max_n ?? 1;
  await imageStore.generate(prompt.value, {
    ...options.value,
    n: clampCount(options.value.n, maxN)
  });
}

function clearPrompt() {
  prompt.value = "";
}
</script>

<template>
  <section aria-labelledby="generate-title">
    <div class="panel-header">
      <div>
        <h2 id="generate-title">Generate</h2>
        <p>Prompt and output settings</p>
      </div>
    </div>

    <form class="generate-form" @submit.prevent="submit">
      <label class="field">
        <span>Prompt</span>
        <textarea
          v-model="prompt"
          rows="9"
          placeholder="A clean product render of a white ceramic mug on a walnut desk"
          :disabled="imageStore.isGenerating"
        />
      </label>

      <ParameterControls
        v-model="options"
        :config="imageStore.config"
        :disabled="imageStore.isGenerating"
      />

      <div class="button-row">
        <button
          class="button button-secondary"
          type="button"
          :disabled="imageStore.isGenerating || prompt.length === 0"
          @click="clearPrompt"
        >
          <Eraser :size="16" aria-hidden="true" />
          <span>Clear</span>
        </button>
        <button class="button button-primary" type="submit" :disabled="!canGenerate">
          <Sparkles :size="16" aria-hidden="true" />
          <span>{{ imageStore.isGenerating ? "Generating" : "Generate" }}</span>
        </button>
      </div>
    </form>
  </section>
</template>
