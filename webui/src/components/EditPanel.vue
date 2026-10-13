<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { ArrowDown, ArrowUp, ImagePlus, LoaderCircle, Trash2, Upload, WandSparkles, X } from "@lucide/vue";
import ParameterControls from "./ParameterControls.vue";
import ParameterPresets from "./ParameterPresets.vue";
import { validateDraft } from "../parameters";
import { useImageStore } from "../stores/imageStore";
import type { UploadedImageAsset } from "../types/image";

const imageStore = useImageStore();
const fileInput = ref<HTMLInputElement | null>(null);
const maskInput = ref<HTMLInputElement | null>(null);
const isDragging = ref(false);
const selectedAssetId = ref<string | null>(null);
const draft = computed(() => imageStore.drafts.edit);
const prompt = computed({ get: () => draft.value.prompt, set: value => imageStore.updateDraft("edit", { ...draft.value, prompt: value }) });
const options = computed({ get: () => draft.value.options, set: value => imageStore.updateDraft("edit", { ...draft.value, options: value }) });
const selectedAsset = computed<UploadedImageAsset | null>(() => imageStore.uploadedAssets.find(asset => asset.id === selectedAssetId.value) ?? null);
const validation = computed(() => validateDraft(draft.value, imageStore.config, "edit"));
const canEdit = computed(() => Boolean(imageStore.config) && imageStore.editInputs.length > 0 && !imageStore.isBusy && !Object.keys(validation.value.errors).length);
const promptError = computed(() => imageStore.fieldErrors.edit.prompt || (prompt.value ? validation.value.errors.prompt : ""));
watch(() => imageStore.uploadedAssets.length, () => { if (!selectedAssetId.value && imageStore.uploadedAssets.length) selectedAssetId.value = imageStore.uploadedAssets[0].id; }, { immediate: true });
function openFilePicker() { fileInput.value?.click(); }
async function addFiles(fileList: FileList | File[] | null) {
  const previousCount = imageStore.uploadedAssets.length;
  await imageStore.addUploadedFiles(Array.from(fileList ?? []));
  selectedAssetId.value = imageStore.uploadedAssets[previousCount]?.id ?? imageStore.uploadedAssets[0]?.id ?? null;
}
function handleFileInput(event: Event) { const input = event.target as HTMLInputElement; void addFiles(input.files); input.value = ""; }
function handleDrop(event: DragEvent) { isDragging.value = false; void addFiles(event.dataTransfer?.files ?? null); }
function handlePaste(event: ClipboardEvent) {
  const files = Array.from(event.clipboardData?.files ?? []);
  if (files.length) { event.preventDefault(); void addFiles(files); }
}
function removeAsset(assetId: string) {
  imageStore.removeUploadedAsset(assetId);
  if (selectedAssetId.value === assetId) selectedAssetId.value = imageStore.uploadedAssets[0]?.id ?? null;
}
function assetQueued(assetId: string) { return imageStore.editInputs.some(input => input.assetId === assetId); }
function addAsset(assetId: string) { imageStore.addAssetToEdit(assetId); }
function formatBytes(value: number) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}
function submit() { void imageStore.submitDraft("edit"); }
function shortcut(event: KeyboardEvent) { if ((event.ctrlKey || event.metaKey) && event.key === "Enter" && !event.isComposing) { event.preventDefault(); if (canEdit.value) submit(); } }
async function selectMask(event: Event) { const input = event.target as HTMLInputElement; if (input.files?.[0]) await imageStore.setEditMask(input.files[0]); input.value = ""; }
</script>

<template>
  <form class="mode-form" @submit.prevent="submit" @keydown="shortcut">
    <ParameterPresets mode="edit" />
    <label class="field">
      <span>编辑指令</span>
      <textarea
        v-model="prompt"
        rows="6"
        :aria-invalid="Boolean(promptError)"
        aria-label="编辑指令"
        aria-describedby="edit-prompt-help"
      />
    </label>

    <small id="edit-prompt-help" :class="promptError ? 'field-error' : 'field-hint'">{{ promptError || `${[...prompt].length} / ${imageStore.config?.max_prompt_length ?? 32000} 字符` }}</small>

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
        @paste="handlePaste"
      >
        <Upload :size="20" aria-hidden="true" />
        <span>点击、拖拽或在此粘贴图片</span>
        <small>PNG、JPEG、WebP · 上传后直接加入输入列表</small>
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
                :title="assetQueued(asset.id) ? '已在输入图片' : '添加到输入图片'"
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
        <h3 id="queue-title">输入图片</h3>
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
              :disabled="index === 0"
              @click="imageStore.moveEditInput(input.id, 'up')"
            >
              <ArrowUp :size="15" aria-hidden="true" />
            </button>
            <button
              class="tool-button"
              type="button"
              title="下移"
              :disabled="index === imageStore.editInputs.length - 1"
              @click="imageStore.moveEditInput(input.id, 'down')"
            >
              <ArrowDown :size="15" aria-hidden="true" />
            </button>
            <button
              class="tool-button danger"
              type="button"
              title="移除"
              @click="imageStore.removeEditInput(input.id)"
            >
              <X :size="15" aria-hidden="true" />
            </button>
          </div>
        </article>
      </div>
      <div v-else class="queue-empty">添加上传图片或历史图片，列表顺序就是模型收到的输入顺序。</div>
    </section>

    <p v-if="imageStore.fieldErrors.edit.images" class="field-error">{{ imageStore.fieldErrors.edit.images }}</p>
    <section class="edit-section" aria-labelledby="mask-title">
      <div class="section-heading"><h3 id="mask-title">局部编辑蒙版（可选）</h3><button v-if="imageStore.editMask" type="button" class="text-button" @click="imageStore.clearEditMask">清除蒙版</button></div>
      <button type="button" class="button button-secondary" @click="maskInput?.click()">{{ imageStore.editMask?.filename ?? "上传 PNG 蒙版" }}</button>
      <input ref="maskInput" class="file-input" type="file" accept="image/png" @change="selectMask" />
      <img v-if="imageStore.editMask" :src="imageStore.editMask.previewUrl" class="mask-preview" alt="蒙版透明区域预览" />
      <small class="field-hint">透明区域指定编辑范围；蒙版对应列表第一张图片，尺寸须一致且小于 4 MB。{{ imageStore.editMask ? `${imageStore.editMask.width} × ${imageStore.editMask.height}` : '' }}</small>
      <small v-if="imageStore.fieldErrors.edit.mask" class="field-error">{{ imageStore.fieldErrors.edit.mask }}</small>
    </section>

    <ParameterControls
      v-model="options"
      :config="imageStore.config"
      :errors="imageStore.fieldErrors.edit"
      mode="edit"
    />

    <div class="submit-area"><p v-if="imageStore.isBusy" class="field-hint">可以继续修改草稿；本次请求使用提交时的图片和设置。</p><button class="button button-primary edit-submit" type="submit" :disabled="!canEdit"><LoaderCircle v-if="imageStore.isEditing" class="loading-icon" :size="16" aria-hidden="true" /><WandSparkles v-else :size="16" aria-hidden="true" /><span>{{ imageStore.isBusy ? "等待当前任务" : "编辑图片" }}</span></button><small class="field-hint">Ctrl / ⌘ + Enter 提交</small></div>
  </form>
</template>
