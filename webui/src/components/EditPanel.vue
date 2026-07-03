<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  ArrowDown,
  ArrowUp,
  ImagePlus,
  LoaderCircle,
  Trash2,
  Upload,
  WandSparkles,
  X
} from "@lucide/vue";
import ParameterControls from "./ParameterControls.vue";
import { useImageStore } from "../stores/imageStore";
import type { EditOptions, ImageOptions, UploadedImageAsset } from "../types/image";

const imageStore = useImageStore();
const fileInput = ref<HTMLInputElement | null>(null);
const prompt = ref("");
const isDragging = ref(false);
const selectedAssetId = ref<string | null>(null);
const options = ref<ImageOptions>({
  model: undefined,
  size: "1024x1024",
  quality: "auto",
  output_format: "png",
  moderation: "none",
  n: 1
});

const selectedAsset = computed<UploadedImageAsset | null>(
  () => imageStore.uploadedAssets.find((asset) => asset.id === selectedAssetId.value) ?? null
);
const canEdit = computed(
  () => prompt.value.trim().length > 0 && imageStore.editInputs.length > 0 && !imageStore.isBusy
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
  () => imageStore.uploadedAssets.length,
  () => {
    if (!selectedAssetId.value && imageStore.uploadedAssets.length > 0) {
      selectedAssetId.value = imageStore.uploadedAssets[0].id;
    }
  }
);

function clampCount(value: number, max: number): number {
  return Math.max(1, Math.min(max, Math.round(value || 1)));
}

function openFilePicker() {
  fileInput.value?.click();
}

async function addFiles(fileList: FileList | File[] | null) {
  const files = Array.from(fileList ?? []);
  if (files.length === 0) {
    return;
  }

  const previousCount = imageStore.uploadedAssets.length;
  await imageStore.addUploadedFiles(files);
  selectedAssetId.value =
    imageStore.uploadedAssets[previousCount]?.id ??
    imageStore.uploadedAssets[imageStore.uploadedAssets.length - 1]?.id ??
    selectedAssetId.value;
}

function handleFileInput(event: Event) {
  const input = event.target as HTMLInputElement;
  void addFiles(input.files);
  input.value = "";
}

function handleDrop(event: DragEvent) {
  isDragging.value = false;
  void addFiles(event.dataTransfer?.files ?? null);
}

function removeAsset(assetId: string) {
  imageStore.removeUploadedAsset(assetId);
  if (selectedAssetId.value === assetId) {
    selectedAssetId.value = imageStore.uploadedAssets[0]?.id ?? null;
  }
}

function assetQueued(assetId: string): boolean {
  return imageStore.editInputs.some((input) => input.assetId === assetId);
}

function addAsset(assetId: string) {
  imageStore.addAssetToEdit(assetId);
}

function formatBytes(value: number): string {
  if (value < 1024) {
    return `${value} B`;
  }

  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }

  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

async function submit() {
  if (!canEdit.value) {
    return;
  }

  const maxN = imageStore.config?.max_n ?? 1;
  const editOptions: EditOptions = {
    model: options.value.model,
    size: options.value.size,
    quality: options.value.quality,
    output_format: options.value.output_format,
    moderation: options.value.moderation,
    n: clampCount(options.value.n, maxN)
  };

  await imageStore.edit(prompt.value, editOptions);
}
</script>

<template>
  <form class="mode-form" @submit.prevent="submit">
    <label class="field">
      <span>编辑指令</span>
      <textarea
        v-model="prompt"
        rows="6"
        :disabled="imageStore.isBusy"
      />
    </label>

    <section class="edit-section" aria-labelledby="upload-title">
      <div class="section-heading">
        <h3 id="upload-title">上传图片</h3>
        <small>{{ imageStore.uploadedAssets.length }} 张</small>
      </div>

      <div
        class="upload-dropzone"
        :class="{ dragging: isDragging }"
        role="button"
        tabindex="0"
        @click="openFilePicker"
        @keydown.enter.prevent="openFilePicker"
        @keydown.space.prevent="openFilePicker"
        @dragenter.prevent="isDragging = true"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="handleDrop"
      >
        <Upload :size="20" aria-hidden="true" />
        <span>点击或拖拽上传多张图片</span>
        <small>PNG、JPEG、WebP</small>
      </div>
      <input
        ref="fileInput"
        class="file-input"
        type="file"
        accept="image/png,image/jpeg,image/webp"
        multiple
        @change="handleFileInput"
      />

      <div v-if="imageStore.uploadedAssets.length" class="asset-layout">
        <div class="asset-grid" role="list" aria-label="已上传图片">
          <article
            v-for="asset in imageStore.uploadedAssets"
            :key="asset.id"
            class="asset-card"
            :class="{ selected: asset.id === selectedAssetId }"
            role="listitem"
          >
            <button class="asset-preview-button" type="button" @click="selectedAssetId = asset.id">
              <img :src="asset.previewUrl" :alt="asset.filename" />
            </button>
            <div class="asset-card-meta">
              <strong>{{ asset.filename }}</strong>
              <small>
                {{ asset.width || "-" }}x{{ asset.height || "-" }} /
                {{ formatBytes(asset.sizeBytes) }}
              </small>
            </div>
            <div class="asset-card-actions">
              <button
                class="tool-button"
                type="button"
                :disabled="assetQueued(asset.id)"
                :title="assetQueued(asset.id) ? '已在编辑队列' : '添加到编辑队列'"
                @click="addAsset(asset.id)"
              >
                <ImagePlus :size="15" aria-hidden="true" />
              </button>
              <button
                class="tool-button danger"
                type="button"
                title="删除上传图片"
                @click="removeAsset(asset.id)"
              >
                <Trash2 :size="15" aria-hidden="true" />
              </button>
            </div>
          </article>
        </div>

        <div v-if="selectedAsset" class="asset-inspector">
          <img :src="selectedAsset.previewUrl" :alt="selectedAsset.filename" />
          <div>
            <strong>{{ selectedAsset.filename }}</strong>
            <span>
              {{ selectedAsset.width || "-" }}x{{ selectedAsset.height || "-" }} /
              {{ formatBytes(selectedAsset.sizeBytes) }}
            </span>
          </div>
        </div>
      </div>
    </section>

    <section class="edit-section" aria-labelledby="queue-title">
      <div class="section-heading">
        <h3 id="queue-title">编辑队列</h3>
        <small>{{ imageStore.editInputs.length }} 张</small>
      </div>

      <div v-if="imageStore.editInputs.length" class="edit-queue" role="list">
        <article
          v-for="(input, index) in imageStore.editInputs"
          :key="input.id"
          class="queue-item"
          role="listitem"
        >
          <span class="queue-index">{{ index + 1 }}</span>
          <img :src="input.previewUrl" :alt="input.filename" />
          <div class="queue-copy">
            <strong>{{ input.filename }}</strong>
            <small>{{ input.source === "upload" ? "上传图片" : "历史图片" }}</small>
          </div>
          <div class="queue-actions">
            <button
              class="tool-button"
              type="button"
              title="上移"
              :disabled="index === 0 || imageStore.isBusy"
              @click="imageStore.moveEditInput(input.id, 'up')"
            >
              <ArrowUp :size="15" aria-hidden="true" />
            </button>
            <button
              class="tool-button"
              type="button"
              title="下移"
              :disabled="index === imageStore.editInputs.length - 1 || imageStore.isBusy"
              @click="imageStore.moveEditInput(input.id, 'down')"
            >
              <ArrowDown :size="15" aria-hidden="true" />
            </button>
            <button
              class="tool-button danger"
              type="button"
              title="移除"
              :disabled="imageStore.isBusy"
              @click="imageStore.removeEditInput(input.id)"
            >
              <X :size="15" aria-hidden="true" />
            </button>
          </div>
        </article>
      </div>
      <div v-else class="queue-empty">从已上传图片添加素材后，队列顺序就是编辑输入顺序。</div>
    </section>

    <ParameterControls
      v-model="options"
      :config="imageStore.config"
      :disabled="imageStore.isBusy"
      mode="edit"
    />

    <button class="button button-primary edit-submit" type="submit" :disabled="!canEdit">
      <LoaderCircle v-if="imageStore.isEditing" class="loading-icon" :size="16" aria-hidden="true" />
      <WandSparkles v-else :size="16" aria-hidden="true" />
      <span>{{ imageStore.isEditing ? "编辑中" : "编辑图片" }}</span>
    </button>
  </form>
</template>
