export type AppMode = "generate" | "edit";

export interface AppConfig {
  default_model: string;
  models: string[];
  sizes: string[];
  qualities: string[];
  formats: string[];
  backgrounds: string[];
  moderations: string[];
  input_fidelities: string[];
  styles: string[];
  response_formats: string[];
  max_n: number;
  max_prompt_length: number;
}

export interface ImageOptions {
  model?: string;
  size: string;
  quality: string;
  output_format: string;
  moderation?: string;
  background?: string;
  output_compression?: number;
  input_fidelity?: string;
  style?: string;
  response_format?: string;
  timeout?: number;
  extra_body?: Record<string, unknown>;
  n: number;
}

export type EditOptions = ImageOptions;

export type ParameterDraft = Record<
  "model" | "size" | "quality" | "output_format" | "background" |
  "moderation" | "n" | "output_compression" | "input_fidelity" |
  "style" | "response_format" | "timeout" | "extra_body", string
>;

export interface PromptDraft {
  prompt: string;
  options: ParameterDraft;
}

export interface ParameterPreset {
  name: string;
  options: ParameterDraft;
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
  source_order?: string[] | null;
  mask_filename?: string | null;
  options?: ImageOptions | null;
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
  error_fields?: Record<string, string>;
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
