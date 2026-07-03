<script setup lang="ts">
import { computed } from "vue";
import { AlertTriangle, Edit3, Trash2 } from "@lucide/vue";
import { resolveAssetUrl } from "../api/client";
import { useImageStore } from "../stores/imageStore";
import type { GenerationJob, ImageRecord } from "../types/image";

type HistoryItem =
  | {
      type: "image";
      id: string;
      sortTime: string;
      image: ImageRecord;
    }
  | {
      type: "failed";
      id: string;
      sortTime: string;
      job: GenerationJob;
    };

const imageStore = useImageStore();
const images = computed(() => imageStore.historyImages);
const failedJobs = computed(() => imageStore.failedJobs);
const historyItems = computed<HistoryItem[]>(() =>
  [
    ...images.value.map((image) => ({
      type: "image" as const,
      id: image.id,
      sortTime: image.created_at,
      image
    })),
    ...failedJobs.value.map((job) => ({
      type: "failed" as const,
      id: job.id,
      sortTime: job.updated_at || job.created_at,
      job
    }))
  ].sort((a, b) => b.sortTime.localeCompare(a.sortTime))
);

function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

function addToEdit(imageId: string) {
  imageStore.addHistoryImageToEdit(imageId);
}

async function removeImage(id: string) {
  await imageStore.deleteImage(id);
}

async function removeFailedJob(id: string) {
  await imageStore.deleteFailedJob(id);
}

async function removeHistoryItem(item: HistoryItem) {
  if (item.type === "image") {
    await removeImage(item.image.id);
    return;
  }

  await removeFailedJob(item.job.id);
}
</script>

<template>
  <section aria-labelledby="history-title">
    <div class="panel-header">
      <div>
        <h2 id="history-title">历史</h2>
        <p>{{ images.length }} 张图片</p>
      </div>
    </div>

    <div v-if="historyItems.length" class="history-list" role="list">
      <div
        v-for="item in historyItems"
        :key="`${item.type}-${item.id}`"
        class="history-item"
        :class="{
          selected:
            item.type === 'image'
              ? item.image.id === imageStore.selectedImageId
              : item.job.id === imageStore.selectedJobId,
          failed: item.type === 'failed'
        }"
        role="listitem"
      >
        <button
          v-if="item.type === 'image'"
          class="history-select"
          type="button"
          @click="imageStore.selectImage(item.image.id)"
        >
          <img :src="resolveAssetUrl(item.image.url)" :alt="item.image.prompt" />
          <span class="history-copy">
            <strong>{{ item.image.prompt }}</strong>
            <small>
              {{ item.image.type === "edit" ? "编辑" : "生成" }} /
              {{ item.image.size }} / {{ item.image.quality }} /
              {{ formatTimestamp(item.image.created_at) }}
            </small>
          </span>
        </button>

        <button
          v-else
          class="history-select history-failed-select"
          type="button"
          @click="imageStore.selectJob(item.job.id)"
        >
          <span class="history-failed-icon" aria-hidden="true">
            <AlertTriangle :size="20" />
          </span>
          <span class="history-copy">
            <strong>{{ item.job.prompt }}</strong>
            <small>生成失败 / {{ formatTimestamp(item.job.updated_at) }}</small>
          </span>
        </button>

        <div class="history-actions">
          <button
            v-if="item.type === 'image'"
            class="history-action"
            type="button"
            title="添加到编辑"
            aria-label="添加到编辑"
            :disabled="imageStore.isBusy"
            @click="addToEdit(item.image.id)"
          >
            <Edit3 :size="15" aria-hidden="true" />
          </button>
          <button
            class="history-action danger"
            type="button"
            title="删除"
            aria-label="删除"
            :disabled="imageStore.isBusy"
            @click="removeHistoryItem(item)"
          >
            <Trash2 :size="15" aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>

    <div v-else class="history-empty">暂无历史</div>
  </section>
</template>
