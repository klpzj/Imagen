<script setup lang="ts">
import { Edit3, Sparkles } from "@lucide/vue";
import EditPanel from "./EditPanel.vue";
import GeneratePanel from "./GeneratePanel.vue";
import { useImageStore } from "../stores/imageStore";

defineProps<{
  reuseRequest: { prompt: string; token: number } | null;
}>();

const imageStore = useImageStore();
</script>

<template>
  <section aria-labelledby="mode-title">
    <div class="panel-header mode-header">
      <div>
        <h2 id="mode-title">{{ imageStore.mode === "generate" ? "生成" : "编辑" }}</h2>
        <p>{{ imageStore.mode === "generate" ? "提示词与输出设置" : "多图片上传与编辑队列" }}</p>
      </div>
      <div class="mode-switch" role="tablist" aria-label="工作模式">
        <button
          type="button"
          role="tab"
          :aria-selected="imageStore.mode === 'generate'"
          :class="{ active: imageStore.mode === 'generate' }"
          @click="imageStore.setMode('generate')"
        >
          <Sparkles :size="15" aria-hidden="true" />
          <span>生成</span>
        </button>
        <button
          type="button"
          role="tab"
          :aria-selected="imageStore.mode === 'edit'"
          :class="{ active: imageStore.mode === 'edit' }"
          @click="imageStore.setMode('edit')"
        >
          <Edit3 :size="15" aria-hidden="true" />
          <span>编辑</span>
        </button>
      </div>
    </div>

    <GeneratePanel v-if="imageStore.mode === 'generate'" :reuse-request="reuseRequest" />
    <EditPanel v-else />
  </section>
</template>
