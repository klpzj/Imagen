const FALLBACK_API_BASE = "";

export const API_BASE = normalizeBase(
  import.meta.env.VITE_API_BASE ?? FALLBACK_API_BASE
);

interface ApiErrorBody {
  detail?: {
    message?: string;
    code?: string;
  } | string;
}

export class ApiError extends Error {
  code?: string;
  status: number;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

function normalizeBase(base: string): string {
  return base.replace(/\/+$/, "");
}

export async function parseApiError(response: Response): Promise<ApiError> {
  let body: ApiErrorBody | null = null;

  try {
    body = (await response.json()) as ApiErrorBody;
  } catch {
    body = null;
  }

  if (typeof body?.detail === "string") {
    return new ApiError(body.detail, response.status);
  }

  const message = body?.detail?.message ?? "图像服务返回错误。";
  return new ApiError(message, response.status, body?.detail?.code);
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init.headers
    }
  });

  if (!response.ok) {
    throw await parseApiError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export function resolveAssetUrl(url: string): string {
  if (/^https?:\/\//i.test(url)) {
    return url;
  }

  return `${API_BASE}${url.startsWith("/") ? "" : "/"}${url}`;
}

export async function downloadAsset(url: string, filename: string): Promise<void> {
  const response = await fetch(resolveAssetUrl(url));
  if (!response.ok) {
    throw await parseApiError(response);
  }

  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}
