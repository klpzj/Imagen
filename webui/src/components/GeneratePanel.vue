<script setup lang="ts">
import { computed } from "vue";
import { Eraser, Sparkles } from "@lucide/vue";
import ParameterControls from "./ParameterControls.vue";
import ParameterPresets from "./ParameterPresets.vue";
import { validateDraft } from "../parameters";
import { useImageStore } from "../stores/imageStore";

const imageStore = useImageStore();
const draft = computed(() => imageStore.drafts.generate);
const prompt = computed({ get: () => draft.value.prompt, set: value => imageStore.updateDraft("generate", { ...draft.value, prompt: value }) });
const options = computed({ get: () => draft.value.options, set: value => imageStore.updateDraft("generate", { ...draft.value, options: value }) });
const validation = computed(() => validateDraft(draft.value, imageStore.config, "generate"));
const canGenerate = computed(() => Boolean(imageStore.config) && !imageStore.isBusy && !Object.keys(validation.value.errors).length);
const promptError = computed(() => imageStore.fieldErrors.generate.prompt || (prompt.value ? validation.value.errors.prompt : ""));
function submit() { void imageStore.submitDraft("generate"); }
function shortcut(event: KeyboardEvent) { if ((event.ctrlKey || event.metaKey) && event.key === "Enter" && !event.isComposing) { event.preventDefault(); if (canGenerate.value) submit(); } }
function clearPrompt() { imageStore.rememberDraft("generate"); prompt.value = ""; }
</script>

<template>
  <form class="mode-form" @submit.prevent="submit" @keydown="shortcut">
    <ParameterPresets mode="generate" />
    <label class="field"><span>提示词</span><textarea v-model="prompt" rows="7" aria-label="提示词" :aria-invalid="Boolean(promptError)" aria-describedby="generate-prompt-help" /></label>
    <small id="generate-prompt-help" :class="promptError ? 'field-error' : 'field-hint'">{{ promptError || `${[...prompt].length} / ${imageStore.config?.max_prompt_length ?? 32000} 字符` }}</small>
    <ParameterControls v-model="options" :config="imageStore.config" :errors="imageStore.fieldErrors.generate" mode="generate" />
    <p v-if="imageStore.fieldErrors.generate.options" class="field-error">{{ imageStore.fieldErrors.generate.options }}</p>
    <div class="submit-area"><p v-if="imageStore.isBusy" class="field-hint">可以继续修改草稿；运行中的任务仍使用提交时的设置。</p><div class="button-row"><button class="button button-secondary" type="button" :disabled="!prompt.length" @click="clearPrompt"><Eraser :size="16" /><span>清空</span></button><button class="button button-primary" type="submit" :disabled="!canGenerate"><Sparkles :size="16" /><span>{{ imageStore.isBusy ? "等待当前任务" : "生成图片" }}</span></button></div><small class="field-hint">Ctrl / ⌘ + Enter 提交 · 参数和提示词自动保留</small></div>
  </form>
</template>
