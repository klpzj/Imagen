<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";
import { ImageIcon } from "@lucide/vue";
import HistoryGallery from "./HistoryGallery.vue";
import ImagePreview from "./ImagePreview.vue";
import ModePanel from "./ModePanel.vue";
import { useImageStore } from "../stores/imageStore";

type ResizeSide = "left" | "right";

const imageStore = useImageStore();
const reuseRequest = ref<{ prompt: string; token: number } | null>(null);
const leftWidth = ref(380);
const rightWidth = ref(320);

let activeResize:
  | {
      side: ResizeSide;
      startX: number;
      startWidth: number;
    }
  | null = null;

const activeImage = computed(
  () => imageStore.selectedImage ?? imageStore.latestImage
);

const modelLabel = computed(() => {
  if (activeImage.value) {
    return activeImage.value.model;
  }

  return imageStore.config?.default_model ?? "加载中";
});

const statusLabel = computed(() => {
  if (imageStore.isEditing) {
    return "编辑中";
  }

  if (imageStore.isGenerating) {
    return "生成中";
  }

  return "就绪";
});

const workspaceStyle = computed(() => ({
  "--left-width": `${leftWidth.value}px`,
  "--right-width": `${rightWidth.value}px`
}));

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function reusePrompt(prompt: string) {
  reuseRequest.value = {
    prompt,
    token: Date.now()
  };
  imageStore.setMode("generate");
}

function addPreviewToEdit(imageId: string) {
  imageStore.addHistoryImageToEdit(imageId);
}

function startResize(side: ResizeSide, event: PointerEvent) {
  activeResize = {
    side,
    startX: event.clientX,
    startWidth: side === "left" ? leftWidth.value : rightWidth.value
  };

  document.body.classList.add("is-resizing");
  window.addEventListener("pointermove", handleResize);
  window.addEventListener("pointerup", stopResize);
}

function handleResize(event: PointerEvent) {
  if (!activeResize) {
    return;
  }

  const delta = event.clientX - activeResize.startX;
  if (activeResize.side === "left") {
    leftWidth.value = clamp(activeResize.startWidth + delta, 300, 620);
    return;
  }

  rightWidth.value = clamp(activeResize.startWidth - delta, 240, 520);
}

function stopResize() {
  activeResize = null;
  document.body.classList.remove("is-resizing");
  window.removeEventListener("pointermove", handleResize);
  window.removeEventListener("pointerup", stopResize);
}

onBeforeUnmount(() => {
  stopResize();
});
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">
        <ImageIcon :size="20" aria-hidden="true" />
        <div>
          <h1>Imagen 生图工具</h1>
          <p>生成与多图编辑工作台</p>
        </div>
      </div>
      <div class="topbar-status">
        <span>{{ modelLabel }}</span>
        <strong>{{ statusLabel }}</strong>
      </div>
    </header>

    <main class="workspace" :style="workspaceStyle">
      <ModePanel class="left-panel" :reuse-request="reuseRequest" />
      <div
        class="resize-handle resize-handle-left"
        role="separator"
        aria-orientation="vertical"
        aria-label="调整左侧面板宽度"
        @pointerdown="startResize('left', $event)"
      />
      <ImagePreview
        class="preview-panel"
        @reuse-prompt="reusePrompt"
        @add-to-edit="addPreviewToEdit"
      />
      <div
        class="resize-handle resize-handle-right"
        role="separator"
        aria-orientation="vertical"
        aria-label="调整历史面板宽度"
        @pointerdown="startResize('right', $event)"
      />
      <HistoryGallery class="history-panel" />
    </main>
  </div>
</template>
