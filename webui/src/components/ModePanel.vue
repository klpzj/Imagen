<script setup lang="ts">
import { Edit3, Sparkles } from "@lucide/vue";
import EditPanel from "./EditPanel.vue";
import GeneratePanel from "./GeneratePanel.vue";
import { useImageStore } from "../stores/imageStore";

const imageStore = useImageStore();
</script>

<template>
  <section aria-labelledby="mode-title">
    <div class="panel-header mode-header">
      <div>
        <h2 id="mode-title">{{ imageStore.mode === "generate" ? "生成" : "编辑" }}</h2>
        <p>{{ imageStore.storageAvailable ? "草稿自动保存在本机" : "草稿保留在当前页面" }}</p>
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

    <div v-if="imageStore.notice" class="workspace-notice" role="status"><span>{{ imageStore.notice }}</span><button type="button" aria-label="关闭提示" @click="imageStore.notice = null">×</button></div>
    <div v-if="imageStore.missingUploadNames.length" class="workspace-notice missing-assets"><span>这些上传文件需重新添加：{{ imageStore.missingUploadNames.join('、') }}。添加后请核对输入顺序与第一张图片。</span><button type="button" @click="imageStore.missingUploadNames = []">忽略缺失素材</button></div>
    <GeneratePanel v-if="imageStore.mode === 'generate'" />
    <EditPanel v-else />
  </section>
</template>
