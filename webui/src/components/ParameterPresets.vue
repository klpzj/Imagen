<script setup lang="ts">
import { computed, ref, useId } from "vue";
import EditableCombobox from "./EditableCombobox.vue";
import { useImageStore } from "../stores/imageStore";
import type { AppMode } from "../types/image";

const props = defineProps<{ mode: AppMode }>();
const store = useImageStore();
const name = ref("");
const importInput = ref<HTMLInputElement | null>(null);
const id = useId();
const suggestions = computed(() => store.presets.map(preset => preset.name));
function apply(value = name.value) { if (suggestions.value.includes(value)) store.applyPreset(props.mode, value); }
async function importPreset(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (file) {
    try { store.importPreset(props.mode, JSON.parse(await file.text())); }
    catch { store.notice = "导入失败，请选择 Imagen 参数 JSON 文件。"; }
  }
  input.value = "";
}
function exportPreset() {
  const blob = new Blob([JSON.stringify({ name: name.value.trim() || "我的参数", options: store.drafts[props.mode].options }, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a"); link.href = url; link.download = "imagen-parameters.json"; link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
</script>

<template>
  <div class="preset-controls">
    <EditableCombobox v-model="name" label="参数预设" :suggestions="suggestions" placeholder="选择预设，或输入新名称" @select="apply" />
    <div class="preset-actions">
      <button type="button" :disabled="!name.trim()" @click="store.savePreset(mode, name)">保存预设</button>
      <button type="button" :disabled="!suggestions.includes(name)" @click="apply()">应用</button>
      <button type="button" @click="store.resetParameters(mode)">重置参数</button>
      <button type="button" :disabled="!store.previousDraft" @click="store.undoDraft">撤销</button>
      <button type="button" @click="exportPreset">导出</button>
      <button type="button" @click="importInput?.click()">导入</button>
    </div>
    <input :id="id" ref="importInput" type="file" accept="application/json,.json" hidden @change="importPreset" />
  </div>
</template>
