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

async function parseError(response: Response): Promise<ApiError> {
  let body: ApiErrorBody | null = null;

  try {
    body = (await response.json()) as ApiErrorBody;
  } catch {
    body = null;
  }

  if (typeof body?.detail === "string") {
    return new ApiError(body.detail, response.status);
  }

  const message = body?.detail?.message ?? "The image service returned an error.";
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
    throw await parseError(response);
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
