import { API_BASE, apiFetch, parseApiError } from "./client";
import type {
  AppConfig,
  GeneratePayload,
  GenerationJob,
  ImageRecord
} from "../types/image";

interface ConfigResponse extends AppConfig {}

interface ImagesResponse {
  images: ImageRecord[];
}

interface JobResponse {
  job?: GenerationJob | null;
}

interface JobsResponse {
  jobs: GenerationJob[];
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

export async function editImage(formData: FormData): Promise<ImageRecord[]> {
  const response = await fetch(`${API_BASE}/api/edit`, {
    method: "POST",
    body: formData
  });

  if (!response.ok) {
    throw await parseApiError(response);
  }

  const data = (await response.json()) as ImagesResponse;
  return data.images;
}

export async function createGenerationJob(
  payload: GeneratePayload
): Promise<GenerationJob> {
  const response = await apiFetch<JobResponse>("/api/jobs", {
    method: "POST",
    body: JSON.stringify(payload)
  });

  if (!response.job) {
    throw new Error("任务创建失败。");
  }

  return response.job;
}

export async function getGenerationJob(jobId: string): Promise<GenerationJob> {
  const response = await apiFetch<JobResponse>(
    `/api/jobs/${encodeURIComponent(jobId)}`
  );

  if (!response.job) {
    throw new Error("任务不存在。");
  }

  return response.job;
}

export async function getActiveGenerationJob(): Promise<GenerationJob | null> {
  const response = await apiFetch<JobResponse>("/api/jobs/active");
  return response.job ?? null;
}

export async function listGenerationJobs(): Promise<GenerationJob[]> {
  const response = await apiFetch<JobsResponse>("/api/jobs");
  return response.jobs;
}

export async function deleteGenerationJob(
  jobId: string
): Promise<GenerationJob[]> {
  const response = await apiFetch<JobsResponse>(
    `/api/jobs/${encodeURIComponent(jobId)}`,
    {
      method: "DELETE"
    }
  );

  return response.jobs;
}

export async function deleteImage(imageId: string): Promise<ImageRecord[]> {
  const response = await apiFetch<ImagesResponse>(
    `/api/images/${encodeURIComponent(imageId)}`,
    {
      method: "DELETE"
    }
  );

  return response.images;
}
