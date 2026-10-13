const FALLBACK_API_BASE = "";

function hostedToolBase(): string {
  if (typeof window === "undefined") {
    return FALLBACK_API_BASE;
  }

  // When the Vue app is opened through PersonalStation's same-origin BFF,
  // keep /api and /outputs under the station path. A standalone Imagen build
  // still falls back to the root-relative Vite proxy.
  const match = window.location.pathname.match(
    /^(.*)\/workshop\/imagen(?:\/|$)/,
  );
  return match ? `${match[1]}/workshop/imagen` : FALLBACK_API_BASE;
}

export function isEmbeddedInPersonalStation(): boolean {
  return hostedToolBase().length > 0;
}

const configuredApiBase = import.meta.env.VITE_API_BASE?.trim();
export const API_BASE = normalizeBase(configuredApiBase || hostedToolBase());

interface ApiErrorBody {
  detail?:
    | {
        message?: string;
        code?: string;
        fields?: Record<string, string>;
      }
    | string;
  error?:
    | {
        message?: string;
        code?: string;
        fields?: Record<string, string>;
      }
    | string;
  message?: string;
  code?: string;
}

export class ApiError extends Error {
  code?: string;
  status: number;
  fields: Record<string, string>;

  constructor(message: string, status: number, code?: string, fields: Record<string, string> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fields = fields;
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

  const detail = body?.detail ?? body?.error;
  if (typeof detail === "string") {
    return new ApiError(detail, response.status, body?.code);
  }

  const message = detail?.message ?? body?.message ?? "图像服务返回错误。";
  return new ApiError(message, response.status, detail?.code ?? body?.code,
    detail?.fields ?? {});
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
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

export async function downloadAsset(
  url: string,
  filename: string,
): Promise<void> {
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
