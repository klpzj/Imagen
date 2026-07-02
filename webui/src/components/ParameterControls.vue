<script setup lang="ts">
import { computed } from "vue";
import type { AppConfig, ImageOptions } from "../types/image";

const props = defineProps<{
  modelValue: ImageOptions;
  config: AppConfig | null;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: ImageOptions];
}>();

const models = computed(() => props.config?.models ?? []);
const sizes = computed(() => props.config?.sizes ?? []);
const qualities = computed(() => props.config?.qualities ?? []);
const formats = computed(() => props.config?.formats ?? []);
const backgrounds = computed(() => props.config?.backgrounds ?? []);
const maxN = computed(() => props.config?.max_n ?? 1);

function update<Key extends keyof ImageOptions>(
  key: Key,
  value: ImageOptions[Key]
) {
  emit("update:modelValue", {
    ...props.modelValue,
    [key]: value
  });
}

function updateCount(value: string) {
  const parsed = Number.parseInt(value, 10);
  const n = Math.max(1, Math.min(maxN.value, Number.isNaN(parsed) ? 1 : parsed));
  update("n", n);
}
</script>

<template>
  <fieldset class="parameter-grid" :disabled="disabled || !config">
    <legend>Parameters</legend>

    <label class="field">
      <span>Model</span>
      <select
        :value="modelValue.model"
        @change="update('model', ($event.target as HTMLSelectElement).value)"
      >
        <option v-for="model in models" :key="model" :value="model">
          {{ model }}
        </option>
      </select>
    </label>

    <label class="field">
      <span>Size</span>
      <select
        :value="modelValue.size"
        @change="update('size', ($event.target as HTMLSelectElement).value)"
      >
        <option v-for="size in sizes" :key="size" :value="size">
          {{ size }}
        </option>
      </select>
    </label>

    <label class="field">
      <span>Quality</span>
      <select
        :value="modelValue.quality"
        @change="update('quality', ($event.target as HTMLSelectElement).value)"
      >
        <option v-for="quality in qualities" :key="quality" :value="quality">
          {{ quality }}
        </option>
      </select>
    </label>

    <label class="field">
      <span>Format</span>
      <select
        :value="modelValue.output_format"
        @change="update('output_format', ($event.target as HTMLSelectElement).value)"
      >
        <option v-for="format in formats" :key="format" :value="format">
          {{ format }}
        </option>
      </select>
    </label>

    <label class="field">
      <span>Images</span>
      <input
        type="number"
        min="1"
        :max="maxN"
        step="1"
        :value="modelValue.n"
        @input="updateCount(($event.target as HTMLInputElement).value)"
      />
    </label>

    <div class="field field-wide">
      <span>Background</span>
      <div class="segmented" role="radiogroup" aria-label="Background">
        <button
          v-for="background in backgrounds"
          :key="background"
          type="button"
          :class="{ active: modelValue.background === background }"
          :disabled="disabled"
          @click="update('background', background)"
        >
          {{ background }}
        </button>
      </div>
    </div>
  </fieldset>
</template>
