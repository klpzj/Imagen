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
  moderation: "none",
  n: 1
});

const canGenerate = computed(
  () => prompt.value.trim().length > 0 && !imageStore.isBusy
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
      moderation: config.moderations.includes(options.value.moderation)
        ? options.value.moderation
        : "none",
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

watch(
  () => imageStore.activeJob,
  (job) => {
    if (!job || !imageStore.isGenerating) {
      return;
    }

    prompt.value = job.prompt;
    options.value = {
      ...options.value,
      ...job.options
    } as ImageOptions;
  },
  { immediate: true }
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
  <form class="mode-form" @submit.prevent="submit">
    <label class="field">
      <span>提示词</span>
      <textarea
        v-model="prompt"
        rows="9"
        :disabled="imageStore.isBusy"
      />
    </label>

    <ParameterControls
      v-model="options"
      :config="imageStore.config"
      :disabled="imageStore.isBusy"
      mode="generate"
    />

    <div class="button-row">
      <button
        class="button button-secondary"
        type="button"
        :disabled="imageStore.isBusy || prompt.length === 0"
        @click="clearPrompt"
      >
        <Eraser :size="16" aria-hidden="true" />
        <span>清空</span>
      </button>
      <button class="button button-primary" type="submit" :disabled="!canGenerate">
        <Sparkles :size="16" aria-hidden="true" />
        <span>{{ imageStore.isGenerating ? "生成中" : "生成图片" }}</span>
      </button>
    </div>
  </form>
</template>
