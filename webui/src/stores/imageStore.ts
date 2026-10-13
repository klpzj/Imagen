import { defineStore } from "pinia";
import { API_BASE, ApiError, resolveAssetUrl } from "../api/client";
import { defaultParameters, resolveParameters, restoreParameters, validateDraft } from "../parameters";
import {
  createGenerationJob,
  deleteGenerationJob as deleteRemoteGenerationJob,
  deleteImage as deleteRemoteImage,
  editImage,
  getActiveGenerationJob,
  getConfig,
  getGenerationJob,
  listGenerationJobs,
  listImages,
  publishImage as publishRemoteImage,
} from "../api/imageApi";
import type {
  AppConfig,
  AppMode,
  EditInputImage,
  EditOptions,
  GenerationJob,
  ImageOptions,
  ImageRecord,
  UploadedImageAsset,
  PromptDraft,
  ParameterPreset,
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
  publishingImageId: string | null;
  publishedImageIds: string[];
  drafts: Record<AppMode, PromptDraft>;
  presets: ParameterPreset[];
  previousDraft: { mode: AppMode; draft: PromptDraft } | null;
  editMask: UploadedImageAsset | null;
  restoredHistoryIds: string[];
  missingUploadNames: string[];
  fieldErrors: Record<AppMode, Record<string, string>>;
  pendingEdit: { prompt: string; options: EditOptions } | null;
  notice: string | null;
  storageAvailable: boolean;
}

let pollTimer: number | undefined;
const workspaceKey = `imagen.workspace.v1:${API_BASE}`;
const cloneDraft = (draft: PromptDraft): PromptDraft => ({ prompt: draft.prompt, options: { ...draft.options } });

function readWorkspace() {
  const defaults = {
    mode: "generate" as AppMode,
    drafts: { generate: { prompt: "", options: defaultParameters() }, edit: { prompt: "", options: defaultParameters() } },
    presets: [
      { name: "快速试图", options: { ...defaultParameters(), quality: "low" } },
      { name: "高质量输出", options: { ...defaultParameters(), quality: "high" } },
      { name: "横向构图", options: { ...defaultParameters(), size: "1536x1024" } },
    ],
    restoredHistoryIds: [] as string[], missingUploadNames: [] as string[], storageAvailable: true,
  };
  try {
    const saved = JSON.parse(localStorage.getItem(workspaceKey) || "null");
    if (!saved) return defaults;
    for (const mode of ["generate", "edit"] as const) {
      if (saved.drafts?.[mode]) defaults.drafts[mode] = {
        prompt: typeof saved.drafts[mode].prompt === "string" ? saved.drafts[mode].prompt : "",
        options: restoreParameters(saved.drafts[mode].options),
      };
    }
    defaults.mode = saved.mode === "edit" ? "edit" : "generate";
    if (Array.isArray(saved.presets)) defaults.presets = saved.presets
      .filter((item: ParameterPreset) => item && typeof item.name === "string" && item.options && typeof item.options === "object")
      .map((item: ParameterPreset) => ({ name: item.name, options: restoreParameters(item.options) }));
    defaults.restoredHistoryIds = Array.isArray(saved.historyIds) ? saved.historyIds.filter((value: unknown) => typeof value === "string") : [];
    defaults.missingUploadNames = Array.isArray(saved.uploadNames) ? saved.uploadNames.filter((value: unknown) => typeof value === "string") : [];
  } catch { defaults.storageAvailable = false; }
  return defaults;
}

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
  incoming: ImageRecord[],
): ImageRecord[] {
  const byId = new Map<string, ImageRecord>();

  for (const image of [...current, ...incoming]) {
    byId.set(image.id, image);
  }

  return Array.from(byId.values()).sort((a, b) =>
    b.created_at.localeCompare(a.created_at),
  );
}

function mergeJobs(
  current: GenerationJob[],
  incoming: GenerationJob[],
): GenerationJob[] {
  const byId = new Map<string, GenerationJob>();

  for (const job of [...current, ...incoming]) {
    byId.set(job.id, job);
  }

  return Array.from(byId.values()).sort((a, b) =>
    b.created_at.localeCompare(a.created_at),
  );
}

function isActiveJob(job: GenerationJob | null): boolean {
  return job?.status === "queued" || job?.status === "running";
}

function readImageSize(
  url: string,
): Promise<{ width: number; height: number }> {
  return new Promise((resolve) => {
    const image = new Image();
    image.onload = () => {
      resolve({
        width: image.naturalWidth,
        height: image.naturalHeight,
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
  uploadedAssets: UploadedImageAsset[],
  mask: UploadedImageAsset | null,
): FormData {
  const formData = new FormData();
  const assetsById = new Map(uploadedAssets.map((asset) => [asset.id, asset]));

  formData.append("prompt", prompt.trim());
  for (const [key, value] of Object.entries(options)) {
    if (value !== undefined && value !== null) formData.append(key, key === "extra_body" ? JSON.stringify(value) : String(value));
  }
  if (mask) formData.append("mask", mask.file, mask.filename);

  for (const input of editInputs) {
    if (input.source === "upload" && input.assetId) {
      const asset = assetsById.get(input.assetId);
      if (!asset) {
        throw new Error("输入图片已失效，请重新添加。 ");
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
    ...readWorkspace(),
    config: null,
    images: [],
    jobs: [],
    uploadedAssets: [],
    editInputs: [],
    selectedImageId: null,
    selectedJobId: null,
    activeJob: null,
    isGenerating: false,
    isEditing: false,
    error: null,
    publishingImageId: null,
    publishedImageIds: [],
    previousDraft: null,
    editMask: null,
    fieldErrors: { generate: {}, edit: {} },
    pendingEdit: null,
    notice: null,
  }),

  getters: {
    failedJobs: (state): GenerationJob[] =>
      state.jobs.filter((job) => job.status === "failed"),
    selectedFailedJob: (state): GenerationJob | null =>
      state.jobs.find(
        (job) => job.id === state.selectedJobId && job.status === "failed",
      ) ?? null,
    selectedImage: (state): ImageRecord | null => {
      if (state.selectedJobId) {
        return null;
      }

      return (
        state.images.find((image) => image.id === state.selectedImageId) ?? null
      );
    },
    latestImage: (state): ImageRecord | null => state.images[0] ?? null,
    historyImages: (state): ImageRecord[] => state.images,
    isBusy: (state): boolean => state.isGenerating || state.isEditing,
    activeJobPrompt: (state): string | null => state.activeJob?.prompt ?? null,
  },

  actions: {
    matchesSubmission(mode: AppMode, prompt: string, options: ImageOptions | GenerationJob["options"]) {
      const current = resolveParameters(this.drafts[mode].options, this.config, mode);
      const submitted = resolveParameters(restoreParameters(options), this.config, mode);
      const normalize = (values: ImageOptions) => Object.entries({ ...values, model: values.model || this.config?.default_model }).sort(([a], [b]) => a.localeCompare(b));
      return this.drafts[mode].prompt.trim() === prompt.trim()
        && !Object.keys(current.errors).length
        && JSON.stringify(normalize(current.options)) === JSON.stringify(normalize(submitted.options));
    },

    async submitDraft(mode: AppMode) {
      if (!this.config || this.isBusy) return;
      const draft = cloneDraft(this.drafts[mode]);
      const { options, errors } = validateDraft(draft, this.config, mode);
      if (mode === "edit" && !this.editInputs.length) errors.images = "请先添加输入图片。";
      this.fieldErrors[mode] = errors;
      if (Object.keys(errors).length) return;
      if (mode === "generate") await this.generate(draft.prompt, options);
      else await this.edit(draft.prompt, options);
    },

    persistWorkspace() {
      try {
        localStorage.setItem(workspaceKey, JSON.stringify({
          mode: this.mode, drafts: this.drafts, presets: this.presets,
          historyIds: [...new Set([...this.restoredHistoryIds, ...this.editInputs.flatMap(input => input.historyImageId ? [input.historyImageId] : [])])],
          uploadNames: [...new Set([...this.missingUploadNames, ...this.uploadedAssets.map(asset => asset.filename), ...(this.editMask ? [this.editMask.filename] : [])])],
        }));
        this.storageAvailable = true;
      } catch { this.storageAvailable = false; }
    },

    updateDraft(mode: AppMode, value: PromptDraft) {
      this.drafts[mode] = value;
      this.fieldErrors[mode] = {};
    },

    rememberDraft(mode: AppMode) {
      this.previousDraft = { mode, draft: cloneDraft(this.drafts[mode]) };
    },

    undoDraft() {
      if (!this.previousDraft) return;
      const { mode, draft } = this.previousDraft;
      this.drafts[mode] = cloneDraft(draft);
      this.mode = mode;
      this.previousDraft = null;
      this.fieldErrors[mode] = {};
      this.notice = "已恢复此前的提示词与参数。";
    },

    resetParameters(mode: AppMode) {
      this.rememberDraft(mode);
      this.drafts[mode].options = defaultParameters();
      this.fieldErrors[mode] = {};
      this.notice = "参数已重置，提示词保留。可撤销。";
    },

    savePreset(mode: AppMode, name: string) {
      name = name.trim();
      if (!name) return;
      const preset = { name, options: { ...this.drafts[mode].options } };
      const index = this.presets.findIndex(item => item.name === name);
      if (index < 0) this.presets.push(preset);
      else this.presets.splice(index, 1, preset);
      this.notice = `预设“${name}”已保存。`;
    },

    applyPreset(mode: AppMode, name: string) {
      const preset = this.presets.find(item => item.name === name);
      if (!preset) return;
      this.rememberDraft(mode);
      this.drafts[mode].options = { ...preset.options };
      this.fieldErrors[mode] = {};
      this.notice = `已应用“${name}”，提示词保留。可撤销。`;
    },

    importPreset(mode: AppMode, value: unknown) {
      if (!value || typeof value !== "object" || !("options" in value) || !value.options || typeof value.options !== "object" || Array.isArray(value.options)) {
        throw new Error("请选择包含 options 的 Imagen 参数文件。");
      }
      this.rememberDraft(mode);
      this.drafts[mode].options = restoreParameters(value.options);
      this.fieldErrors[mode] = {};
      this.notice = "参数已导入，请核对后再提交。可撤销。";
    },

    reuseImageSettings(image: ImageRecord) {
      const mode = image.type;
      this.rememberDraft(mode);
      this.drafts[mode] = {
        prompt: image.prompt,
        options: restoreParameters(image.options ?? {
          model: image.model, size: image.size, quality: image.quality,
          output_format: image.format, moderation: image.moderation,
        }),
      };
      this.fieldErrors[mode] = {};
      this.mode = mode;
      const warnings: string[] = [];
      if (!image.options) warnings.push("旧记录只有部分参数，其余使用默认值");
      if (mode === "edit") {
        this.editInputs = [];
        this.restoredHistoryIds = [];
        this.missingUploadNames = [];
        const sources = image.source_order ?? image.source_image_ids?.map(id => `history:${id}`) ?? [];
        for (const source of sources) {
          if (source.startsWith("history:")) {
            const id = source.slice(8);
            if (this.images.some(item => item.id === id)) this.addHistoryImageToEdit(id);
            else warnings.push("部分历史素材已删除");
          } else if (source.startsWith("upload:")) {
            this.missingUploadNames.push(source.slice(7));
            warnings.push(`请重新添加 ${source.slice(7)}`);
          }
        }
        if (!image.source_order && (image.source_filenames?.length ?? 0) > (image.source_image_ids?.length ?? 0)) warnings.push("请重新添加原上传图片，并核对输入顺序");
        this.clearEditMask();
        if (image.mask_filename) {
          this.missingUploadNames.push(image.mask_filename);
          warnings.push(`请重新添加蒙版 ${image.mask_filename}`);
        }
        if (warnings.length) warnings.push("请核对输入顺序和第一张图片");
      }
      this.notice = warnings.length ? `设置已复用；${[...new Set(warnings)].join("；")}。` : "已复用提示词和完整设置。";
    },

    reuseJobSettings(job: GenerationJob) {
      this.rememberDraft("generate");
      this.drafts.generate = { prompt: job.prompt, options: restoreParameters(job.options) };
      this.mode = "generate";
      this.fieldErrors.generate = {};
      this.notice = "失败任务的设置已载入，可修改后重新提交。";
    },

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
        if (this.restoredHistoryIds.length) {
          let missing = 0;
          for (const id of this.restoredHistoryIds) {
            const image = this.images.find(item => item.id === id);
            if (image) this.editInputs.push({ id: createId("input"), source: "history", historyImageId: id, previewUrl: resolveAssetUrl(image.url), filename: image.filename });
            else missing++;
          }
          this.restoredHistoryIds = [];
          if (missing) this.notice = `${missing} 张历史素材已不可用，请重新添加并核对输入顺序。`;
        }
        if (
          !this.selectedImageId &&
          !this.selectedJobId &&
          this.images.length > 0
        ) {
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
        if (!size.width || !size.height) {
          URL.revokeObjectURL(previewUrl);
          this.error = "图片无法读取，请检查文件。";
          continue;
        }
        const asset: UploadedImageAsset = {
          id: createId("asset"),
          file,
          previewUrl,
          filename: file.name,
          mimeType: file.type,
          sizeBytes: file.size,
          width: size.width || undefined,
          height: size.height || undefined,
          uploadedAt: Date.now(),
        };
        this.uploadedAssets.push(asset);
        this.addAssetToEdit(asset.id);
        this.missingUploadNames = this.missingUploadNames.filter(name => name !== file.name);
      }
    },

    async setEditMask(file: File) {
      if (file.type !== "image/png" || file.size >= 4 * 1024 * 1024) {
        this.fieldErrors.edit.mask = "请选择小于 4 MB 的 PNG 蒙版。";
        return;
      }
      const previewUrl = URL.createObjectURL(file);
      const size = await readImageSize(previewUrl);
      if (!size.width || !size.height) {
        URL.revokeObjectURL(previewUrl);
        this.fieldErrors.edit.mask = "蒙版无法读取。";
        return;
      }
      this.clearEditMask();
      this.editMask = { id: createId("mask"), file, previewUrl, filename: file.name, mimeType: file.type, sizeBytes: file.size, width: size.width, height: size.height, uploadedAt: Date.now() };
      this.missingUploadNames = this.missingUploadNames.filter(name => name !== file.name);
    },

    clearEditMask() {
      if (this.editMask) URL.revokeObjectURL(this.editMask.previewUrl);
      this.editMask = null;
      delete this.fieldErrors.edit.mask;
    },

    removeUploadedAsset(assetId: string) {
      const asset = this.uploadedAssets.find((item) => item.id === assetId);
      if (asset) {
        URL.revokeObjectURL(asset.previewUrl);
      }

      this.uploadedAssets = this.uploadedAssets.filter(
        (item) => item.id !== assetId,
      );
      this.editInputs = this.editInputs.filter(
        (input) => input.assetId !== assetId,
      );
      delete this.fieldErrors.edit.images;
      delete this.fieldErrors.edit.mask;
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
        filename: asset.filename,
      });
      delete this.fieldErrors.edit.images;
      delete this.fieldErrors.edit.mask;
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
        filename: image.filename,
      });
      delete this.fieldErrors.edit.images;
      delete this.fieldErrors.edit.mask;
      this.mode = "edit";
    },

    removeEditInput(inputId: string) {
      this.editInputs = this.editInputs.filter((input) => input.id !== inputId);
      delete this.fieldErrors.edit.images;
      delete this.fieldErrors.edit.mask;
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
      delete this.fieldErrors.edit.mask;
    },

    async edit(prompt: string, options: EditOptions) {
      if (this.isBusy) return;
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
      this.fieldErrors.edit = {};
      this.pendingEdit = { prompt: trimmedPrompt, options: JSON.parse(JSON.stringify(options)) };
      const sourceSnapshot = JSON.stringify(this.editInputs);
      const maskId = this.editMask?.id;

      try {
        const formData = formatEditForm(
          trimmedPrompt,
          options,
          this.editInputs,
          this.uploadedAssets,
          this.editMask,
        );
        const images = await editImage(formData);
        this.images = mergeNewestFirst(this.images, images);
        this.selectedImageId = images[0]?.id ?? this.selectedImageId;
        this.selectedJobId = null;
        await this.loadHistory();
      } catch (error) {
        this.error = errorMessage(error);
        if (error instanceof ApiError && this.matchesSubmission("edit", trimmedPrompt, options)
          && JSON.stringify(this.editInputs) === sourceSnapshot && this.editMask?.id === maskId) {
          this.fieldErrors.edit = error.fields;
        }
      } finally {
        this.isEditing = false;
        this.pendingEdit = null;
      }
    },

    async generate(prompt: string, options: ImageOptions) {
      if (this.isBusy) return;
      const trimmedPrompt = prompt.trim();
      if (!trimmedPrompt) {
        this.error = "请先输入提示词。";
        return;
      }

      this.isGenerating = true;
      this.error = null;
      this.fieldErrors.generate = {};

      try {
        const job = await createGenerationJob({
          prompt: trimmedPrompt,
          options,
        });
        this.jobs = mergeJobs(this.jobs, [job]);
        this.activeJob = job;
        this.selectedJobId = job.id;
        this.selectedImageId = null;
        this.startPolling(job.id);
      } catch (error) {
        this.isGenerating = false;
        this.error = errorMessage(error);
        if (error instanceof ApiError && this.matchesSubmission("generate", trimmedPrompt, options)) this.fieldErrors.generate = error.fields;
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
          if (this.matchesSubmission("generate", job.prompt, job.options)) this.fieldErrors.generate = job.error_fields ?? {};
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

    async publishImage(id: string) {
      if (this.publishingImageId) {
        return null;
      }

      this.publishingImageId = id;
      this.error = null;
      try {
        const result = await publishRemoteImage(id);
        if (!this.publishedImageIds.includes(id)) {
          this.publishedImageIds.push(id);
        }
        return result.url;
      } catch (error) {
        this.error = errorMessage(error);
        return null;
      } finally {
        this.publishingImageId = null;
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
    },
  },
});
