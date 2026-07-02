import { apiFetch } from "./client";
import type { AppConfig, GeneratePayload, ImageRecord } from "../types/image";

interface ConfigResponse extends AppConfig {}

interface ImagesResponse {
  images: ImageRecord[];
}

export function getConfig(): Promise<AppConfig> {
  return apiFetch<ConfigResponse>("/api/config");
}

export async function listImages(): Promise<ImageRecord[]> {
  const response = await apiFetch<ImagesResponse>("/api/images");
  return response.images;
}

export async function generateImage(
  payload: GeneratePayload
): Promise<ImageRecord[]> {
  const response = await apiFetch<ImagesResponse>("/api/generate", {
    method: "POST",
    body: JSON.stringify(payload)
  });

  return response.images;
}
