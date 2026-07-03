<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  AlertTriangle,
  Clipboard,
  Download,
  Edit3,
  ExternalLink,
  LoaderCircle,
  Maximize2,
  Minus,
  Plus,
  RotateCcw
} from "@lucide/vue";
import { resolveAssetUrl } from "../api/client";
import { useImageStore } from "../stores/imageStore";

const emit = defineEmits<{
  "reuse-prompt": [prompt: string];
  "add-to-edit": [imageId: string];
}>();

const imageStore = useImageStore();
const copied = ref(false);
const zoom = ref(100);
const isFullscreen = ref(false);

const image = computed(() => imageStore.selectedImage ?? imageStore.latestImage);
const failedJob = computed(() => imageStore.selectedFailedJob);
const imageUrl = computed(() => (image.value ? resolveAssetUrl(image.value.url) : ""));
const imageStyle = computed(() => ({
  transform: `scale(${zoom.value / 100})`
}));

watch(
  () => image.value?.id,
  () => {
    zoom.value = 100;
  }
);

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function setZoom(value: number) {
  zoom.value = clamp(Math.round(value), 25, 220);
}

function stepZoom(delta: number) {
  setZoom(zoom.value + delta);
}

function fitImage() {
  zoom.value = 100;
}

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

function openFullscreen() {
  if (image.value) {
    isFullscreen.value = true;
  }
}

function closeFullscreen() {
  isFullscreen.value = false;
}
</script>

<template>
  <section aria-labelledby="preview-title">
    <div class="panel-header preview-header">
      <div>
        <h2 id="preview-title">预览</h2>
        <p>{{ image ? image.filename : failedJob ? "生成失败" : "未选择图片" }}</p>
      </div>
      <div v-if="image" class="preview-zoom" aria-label="图片缩放">
        <button class="tool-button" type="button" title="缩小" @click="stepZoom(-10)">
          <Minus :size="15" aria-hidden="true" />
        </button>
        <input
          class="zoom-range"
          type="range"
          min="25"
          max="220"
          step="5"
          :value="zoom"
          aria-label="缩放比例"
          @input="setZoom(Number(($event.target as HTMLInputElement).value))"
        />
        <button class="tool-button" type="button" title="放大" @click="stepZoom(10)">
          <Plus :size="15" aria-hidden="true" />
        </button>
        <button class="zoom-value" type="button" title="适配窗口" @click="fitImage">
          {{ zoom }}%
        </button>
        <button class="tool-button" type="button" title="全屏预览" @click="openFullscreen">
          <Maximize2 :size="15" aria-hidden="true" />
        </button>
      </div>
    </div>

    <div class="preview-stage">
      <div v-if="imageStore.isBusy" class="preview-loading">
        <LoaderCircle :size="34" aria-hidden="true" />
        <span>{{ imageStore.isEditing ? "正在编辑图片" : "正在生成图片" }}</span>
      </div>
      <div v-else-if="failedJob" class="failed-preview-state">
        <AlertTriangle :size="34" aria-hidden="true" />
        <strong>任务失败</strong>
        <span>{{ failedJob.error ?? "生成失败。" }}</span>
        <p>{{ failedJob.prompt }}</p>
      </div>
      <div v-else-if="image" class="preview-image-scroll">
        <div class="preview-floating-actions" aria-label="图片操作">
          <a
            class="image-action-button"
            :href="imageUrl"
            :download="image.filename"
            title="下载图片"
            aria-label="下载图片"
          >
            <Download :size="16" aria-hidden="true" />
          </a>
          <button
            class="image-action-button"
            type="button"
            :title="copied ? '已复制提示词' : '复制提示词'"
            :aria-label="copied ? '已复制提示词' : '复制提示词'"
            @click="copyPrompt"
          >
            <Clipboard :size="16" aria-hidden="true" />
          </button>
          <button
            class="image-action-button"
            type="button"
            title="复用提示词"
            aria-label="复用提示词"
            @click="emit('reuse-prompt', image.prompt)"
          >
            <RotateCcw :size="16" aria-hidden="true" />
          </button>
          <button
            class="image-action-button"
            type="button"
            title="添加到编辑"
            aria-label="添加到编辑"
            @click="emit('add-to-edit', image.id)"
          >
            <Edit3 :size="16" aria-hidden="true" />
          </button>
          <button
            class="image-action-button"
            type="button"
            title="打开原图"
            aria-label="打开原图"
            @click="openImage"
          >
            <ExternalLink :size="16" aria-hidden="true" />
          </button>
        </div>
        <img class="preview-image" :src="imageUrl" :alt="image.prompt" :style="imageStyle" />
      </div>
      <div v-else class="empty-state">
        <strong>还没有图片</strong>
        <span>生成或编辑完成后，结果会显示在这里。</span>
      </div>
    </div>

    <Teleport to="body">
      <Transition name="fullscreen-preview">
        <div
          v-if="isFullscreen && image"
          class="fullscreen-layer"
          role="dialog"
          aria-modal="true"
          aria-label="全屏图片预览"
          @click.self="closeFullscreen"
        >
          <button class="fullscreen-close" type="button" @click="closeFullscreen">
            关闭
          </button>
          <img class="fullscreen-image" :src="imageUrl" :alt="image.prompt" />
        </div>
      </Transition>
    </Teleport>
  </section>
</template>
