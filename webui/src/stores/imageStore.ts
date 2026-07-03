import { defineStore } from "pinia";
import { resolveAssetUrl } from "../api/client";
import {
  createGenerationJob,
  deleteGenerationJob as deleteRemoteGenerationJob,
  deleteImage as deleteRemoteImage,
  editImage,
  getActiveGenerationJob,
  getConfig,
  getGenerationJob,
  listGenerationJobs,
  listImages
} from "../api/imageApi";
import type {
  AppConfig,
  AppMode,
  EditInputImage,
  EditOptions,
  GenerationJob,
  ImageOptions,
  ImageRecord,
  UploadedImageAsset
} from "../types/image";

interface ImageState {
  config: AppConfig | null;
  images: ImageRecord[];
  jobs: GenerationJob[];
  mode: AppMode;
  uploadedAssets: UploadedImageAsset[];
  editInputs: EditInputImage[];
  selectedImageId: string | null;
  selectedJobId: string | null;
  activeJob: GenerationJob | null;
  isGenerating: boolean;
  isEditing: boolean;
  error: string | null;
}

let pollTimer: number | undefined;

function errorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return "操作失败，请稍后重试。";
}

function createId(prefix: string): string {
  const random =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `${prefix}-${random}`;
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

function mergeJobs(current: GenerationJob[], incoming: GenerationJob[]): GenerationJob[] {
  const byId = new Map<string, GenerationJob>();

  for (const job of [...incoming, ...current]) {
    byId.set(job.id, job);
  }

  return Array.from(byId.values()).sort((a, b) =>
    b.created_at.localeCompare(a.created_at)
  );
}

function isActiveJob(job: GenerationJob | null): boolean {
  return job?.status === "queued" || job?.status === "running";
}

function readImageSize(url: string): Promise<{ width: number; height: number }> {
  return new Promise((resolve) => {
    const image = new Image();
    image.onload = () => {
      resolve({
        width: image.naturalWidth,
        height: image.naturalHeight
      });
    };
    image.onerror = () => resolve({ width: 0, height: 0 });
    image.src = url;
  });
}

function formatEditForm(
  prompt: string,
  options: EditOptions,
  editInputs: EditInputImage[],
  uploadedAssets: UploadedImageAsset[]
): FormData {
  const formData = new FormData();
  const assetsById = new Map(uploadedAssets.map((asset) => [asset.id, asset]));

  formData.append("prompt", prompt.trim());
  if (options.model) {
    formData.append("model", options.model);
  }
  formData.append("size", options.size);
  formData.append("quality", options.quality);
  formData.append("output_format", options.output_format);
  formData.append("moderation", options.moderation);
  formData.append("n", String(options.n));

  for (const input of editInputs) {
    if (input.source === "upload" && input.assetId) {
      const asset = assetsById.get(input.assetId);
      if (!asset) {
        continue;
      }
      formData.append("source_order", `upload:${asset.id}`);
      formData.append("upload_ids", asset.id);
      formData.append("images", asset.file, asset.filename);
      continue;
    }

    if (input.source === "history" && input.historyImageId) {
      formData.append("source_order", `history:${input.historyImageId}`);
      formData.append("image_ids", input.historyImageId);
    }
  }

  return formData;
}

export const useImageStore = defineStore("image", {
  state: (): ImageState => ({
    config: null,
    images: [],
    jobs: [],
    mode: "generate",
    uploadedAssets: [],
    editInputs: [],
    selectedImageId: null,
    selectedJobId: null,
    activeJob: null,
    isGenerating: false,
    isEditing: false,
    error: null
  }),

  getters: {
    failedJobs: (state): GenerationJob[] =>
      state.jobs.filter((job) => job.status === "failed"),
    selectedFailedJob: (state): GenerationJob | null =>
      state.jobs.find(
        (job) => job.id === state.selectedJobId && job.status === "failed"
      ) ?? null,
    selectedImage: (state): ImageRecord | null => {
      if (state.selectedJobId) {
        return null;
      }

      return state.images.find((image) => image.id === state.selectedImageId) ?? null;
    },
    latestImage: (state): ImageRecord | null => state.images[0] ?? null,
    historyImages: (state): ImageRecord[] => state.images,
    isBusy: (state): boolean => state.isGenerating || state.isEditing,
    activeJobPrompt: (state): string | null => state.activeJob?.prompt ?? null
  },

  actions: {
    setMode(mode: AppMode) {
      this.mode = mode;
    },

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
        if (!this.selectedImageId && !this.selectedJobId && this.images.length > 0) {
          this.selectedImageId = this.images[0].id;
        }
      } catch (error) {
        this.error = errorMessage(error);
      }
    },

    async loadJobs() {
      try {
        this.jobs = await listGenerationJobs();
      } catch (error) {
        this.error = errorMessage(error);
      }
    },

    async restoreActiveJob() {
      try {
        const job = await getActiveGenerationJob();
        if (!job) {
          this.activeJob = null;
          this.isGenerating = false;
          this.stopPolling();
          return;
        }

        this.jobs = mergeJobs(this.jobs, [job]);
        this.activeJob = job;
        this.selectedJobId = job.id;
        this.selectedImageId = null;
        this.isGenerating = isActiveJob(job);
        if (isActiveJob(job)) {
          this.startPolling(job.id);
        }
      } catch (error) {
        this.error = errorMessage(error);
      }
    },

    async addUploadedFiles(files: File[]) {
      const validTypes = new Set(["image/png", "image/jpeg", "image/webp"]);

      for (const file of files) {
        if (!validTypes.has(file.type)) {
          this.error = "只能上传 PNG、JPEG 或 WebP 图片。";
          continue;
        }

        const previewUrl = URL.createObjectURL(file);
        const size = await readImageSize(previewUrl);
        this.uploadedAssets.push({
          id: createId("asset"),
          file,
          previewUrl,
          filename: file.name,
          mimeType: file.type,
          sizeBytes: file.size,
          width: size.width || undefined,
          height: size.height || undefined,
          uploadedAt: Date.now()
        });
      }
    },

    removeUploadedAsset(assetId: string) {
      const asset = this.uploadedAssets.find((item) => item.id === assetId);
      if (asset) {
        URL.revokeObjectURL(asset.previewUrl);
      }

      this.uploadedAssets = this.uploadedAssets.filter((item) => item.id !== assetId);
      this.editInputs = this.editInputs.filter((input) => input.assetId !== assetId);
    },

    addAssetToEdit(assetId: string) {
      if (this.editInputs.some((input) => input.assetId === assetId)) {
        return;
      }

      const asset = this.uploadedAssets.find((item) => item.id === assetId);
      if (!asset) {
        return;
      }

      this.editInputs.push({
        id: createId("input"),
        source: "upload",
        assetId: asset.id,
        previewUrl: asset.previewUrl,
        filename: asset.filename
      });
    },

    addHistoryImageToEdit(imageId: string) {
      if (this.editInputs.some((input) => input.historyImageId === imageId)) {
        this.mode = "edit";
        return;
      }

      const image = this.images.find((item) => item.id === imageId);
      if (!image) {
        return;
      }

      this.editInputs.push({
        id: createId("input"),
        source: "history",
        historyImageId: image.id,
        previewUrl: resolveAssetUrl(image.url),
        filename: image.filename
      });
      this.mode = "edit";
    },

    removeEditInput(inputId: string) {
      this.editInputs = this.editInputs.filter((input) => input.id !== inputId);
    },

    moveEditInput(inputId: string, direction: "up" | "down") {
      const index = this.editInputs.findIndex((input) => input.id === inputId);
      if (index < 0) {
        return;
      }

      const targetIndex = direction === "up" ? index - 1 : index + 1;
      if (targetIndex < 0 || targetIndex >= this.editInputs.length) {
        return;
      }

      const nextInputs = [...this.editInputs];
      const [input] = nextInputs.splice(index, 1);
      nextInputs.splice(targetIndex, 0, input);
      this.editInputs = nextInputs;
    },

    async edit(prompt: string, options: EditOptions) {
      const trimmedPrompt = prompt.trim();
      if (!trimmedPrompt) {
        this.error = "请先输入编辑指令。";
        return;
      }

      if (this.editInputs.length === 0) {
        this.error = "请先添加至少一张编辑图片。";
        return;
      }

      this.isEditing = true;
      this.error = null;

      try {
        const formData = formatEditForm(
          trimmedPrompt,
          options,
          this.editInputs,
          this.uploadedAssets
        );
        const images = await editImage(formData);
        this.images = mergeNewestFirst(this.images, images);
        this.selectedImageId = images[0]?.id ?? this.selectedImageId;
        this.selectedJobId = null;
        await this.loadHistory();
      } catch (error) {
        this.error = errorMessage(error);
      } finally {
        this.isEditing = false;
      }
    },

    async generate(prompt: string, options: ImageOptions) {
      const trimmedPrompt = prompt.trim();
      if (!trimmedPrompt) {
        this.error = "请先输入提示词。";
        return;
      }

      this.isGenerating = true;
      this.error = null;

      try {
        const job = await createGenerationJob({
          prompt: trimmedPrompt,
          options
        });
        this.jobs = mergeJobs(this.jobs, [job]);
        this.activeJob = job;
        this.selectedJobId = job.id;
        this.selectedImageId = null;
        this.startPolling(job.id);
      } catch (error) {
        this.isGenerating = false;
        this.error = errorMessage(error);
      }
    },

    startPolling(jobId: string) {
      this.stopPolling();
      void this.refreshJob(jobId);
      pollTimer = window.setInterval(() => {
        void this.refreshJob(jobId);
      }, 1800);
    },

    stopPolling() {
      if (pollTimer !== undefined) {
        window.clearInterval(pollTimer);
        pollTimer = undefined;
      }
    },

    async refreshJob(jobId: string) {
      try {
        const job = await getGenerationJob(jobId);
        this.jobs = mergeJobs(this.jobs, [job]);
        this.activeJob = job;
        this.isGenerating = isActiveJob(job);

        if (isActiveJob(job)) {
          return;
        }

        this.stopPolling();

        if (job.status === "succeeded") {
          this.images = mergeNewestFirst(this.images, job.images);
          this.selectedImageId = job.images[0]?.id ?? this.selectedImageId;
          this.selectedJobId = null;
          await this.loadHistory();
          await this.loadJobs();
          this.activeJob = null;
          return;
        }

        if (job.status === "failed") {
          this.error = job.error ?? "生成失败。";
          this.selectedJobId = job.id;
          this.selectedImageId = null;
          this.activeJob = job;
        }
      } catch (error) {
        this.stopPolling();
        this.isGenerating = false;
        this.error = errorMessage(error);
      }
    },

    selectImage(id: string) {
      this.selectedImageId = id;
      this.selectedJobId = null;
    },

    selectJob(id: string) {
      this.selectedJobId = id;
      this.selectedImageId = null;
    },

    async deleteImage(id: string) {
      try {
        this.images = await deleteRemoteImage(id);
        if (this.selectedImageId === id) {
          this.selectedImageId = this.images[0]?.id ?? null;
        }
      } catch (error) {
        this.error = errorMessage(error);
      }
    },

    async deleteFailedJob(id: string) {
      try {
        this.jobs = await deleteRemoteGenerationJob(id);
        if (this.selectedJobId === id) {
          this.selectedJobId = null;
          this.selectedImageId = this.images[0]?.id ?? null;
        }
        if (this.activeJob?.id === id) {
          this.activeJob = null;
        }
      } catch (error) {
        this.error = errorMessage(error);
      }
    },

    clearError() {
      this.error = null;
    }
  }
});
