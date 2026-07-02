export interface AppConfig {
  default_model: string;
  models: string[];
  sizes: string[];
  qualities: string[];
  formats: string[];
  backgrounds: string[];
  max_n: number;
}

export interface ImageOptions {
  model?: string;
  size: string;
  quality: string;
  output_format: string;
  background?: string | null;
  n: number;
}

export interface GeneratePayload {
  prompt: string;
  options: ImageOptions;
}

export interface ImageRecord {
  id: string;
  type: "generate";
  filename: string;
  url: string;
  prompt: string;
  model: string;
  size: string;
  quality: string;
  format: string;
  created_at: string;
  revised_prompt?: string | null;
}
