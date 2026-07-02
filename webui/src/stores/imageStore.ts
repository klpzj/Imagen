import { defineStore } from "pinia";
import { generateImage, getConfig, listImages } from "../api/imageApi";
import type { AppConfig, ImageOptions, ImageRecord } from "../types/image";

interface ImageState {
  config: AppConfig | null;
  images: ImageRecord[];
  selectedImageId: string | null;
  isGenerating: boolean;
  error: string | null;
}

function errorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return "Something went wrong.";
}

function mergeNewestFirst(
  current: ImageRecord[],
  incoming: ImageRecord[]
): ImageRecord[] {
  const byId = new Map<string, ImageRecord>();

  for (const image of [...incoming, ...current]) {
    byId.set(image.id, image);
  }

  return Array.from(byId.values()).sort((a, b) =>
    b.created_at.localeCompare(a.created_at)
  );
}

export const useImageStore = defineStore("image", {
  state: (): ImageState => ({
    config: null,
    images: [],
    selectedImageId: null,
    isGenerating: false,
    error: null
  }),

  getters: {
    selectedImage: (state): ImageRecord | null =>
      state.images.find((image) => image.id === state.selectedImageId) ?? null,
    latestImage: (state): ImageRecord | null => state.images[0] ?? null,
    historyImages: (state): ImageRecord[] => state.images,
    isBusy: (state): boolean => state.isGenerating
  },

  actions: {
    async loadConfig() {
      try {
        this.config = await getConfig();
      } catch (error) {
        this.error = errorMessage(error);
      }
    },

    async loadHistory() {
      try {
        this.images = await listImages();
        if (!this.selectedImageId && this.images.length > 0) {
          this.selectedImageId = this.images[0].id;
        }
      } catch (error) {
        this.error = errorMessage(error);
      }
    },

    async generate(prompt: string, options: ImageOptions) {
      const trimmedPrompt = prompt.trim();
      if (!trimmedPrompt) {
        this.error = "Enter a prompt before generating.";
        return;
      }

      this.isGenerating = true;
      this.error = null;

      try {
        const images = await generateImage({
          prompt: trimmedPrompt,
          options
        });
        this.images = mergeNewestFirst(this.images, images);
        this.selectedImageId = images[0]?.id ?? this.selectedImageId;
      } catch (error) {
        this.error = errorMessage(error);
      } finally {
        this.isGenerating = false;
      }
    },

    selectImage(id: string) {
      this.selectedImageId = id;
    },

    clearError() {
      this.error = null;
    }
  }
});
