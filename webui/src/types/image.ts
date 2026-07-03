export type AppMode = "generate" | "edit";

export interface AppConfig {
  default_model: string;
  models: string[];
  sizes: string[];
  qualities: string[];
  formats: string[];
  moderations: string[];
  max_n: number;
}

export interface ImageOptions {
  model?: string;
  size: string;
  quality: string;
  output_format: string;
  moderation: string;
  n: number;
}

export interface EditOptions {
  model?: string;
  size: string;
  quality: string;
  output_format: string;
  n: number;
}

export interface GeneratePayload {
  prompt: string;
  options: ImageOptions;
}

export interface ImageRecord {
  id: string;
  type: "generate" | "edit";
  filename: string;
  url: string;
  prompt: string;
  model: string;
  size: string;
  quality: string;
  format: string;
  moderation?: string | null;
  created_at: string;
  revised_prompt?: string | null;
  source_image_ids?: string[] | null;
  source_filenames?: string[] | null;
}

export type GenerationJobStatus = "queued" | "running" | "succeeded" | "failed";

export interface GenerationJob {
  id: string;
  status: GenerationJobStatus;
  prompt: string;
  options: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  images: ImageRecord[];
  error?: string | null;
}

export interface UploadedImageAsset {
  id: string;
  file: File;
  previewUrl: string;
  filename: string;
  mimeType: string;
  sizeBytes: number;
  width?: number;
  height?: number;
  uploadedAt: number;
}

export interface EditInputImage {
  id: string;
  source: "upload" | "history";
  assetId?: string;
  historyImageId?: string;
  previewUrl: string;
  filename: string;
}
