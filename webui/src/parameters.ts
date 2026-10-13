import type { AppConfig, AppMode, ImageOptions, ParameterDraft, PromptDraft } from "./types/image";

export const parameterKeys: (keyof ParameterDraft)[] = [
  "model", "size", "quality", "output_format", "background", "moderation", "n",
  "output_compression", "input_fidelity", "style", "response_format", "timeout", "extra_body",
];

export function defaultParameters(): ParameterDraft {
  return {
    model: "", size: "1024x1024", quality: "auto", output_format: "png",
    background: "", moderation: "", n: "1", output_compression: "",
    input_fidelity: "", style: "", response_format: "", timeout: "", extra_body: "{}",
  };
}

export function restoreParameters(value: unknown): ParameterDraft {
  const result = defaultParameters();
  if (value && typeof value === "object") {
    for (const key of parameterKeys) {
      const item = (value as Record<string, unknown>)[key];
      if (item !== undefined && item !== null) {
        result[key] = key === "extra_body" && typeof item === "object"
          ? JSON.stringify(item, null, 2) : String(item);
      }
    }
  }
  if (result.moderation === "none") result.moderation = "";
  return result;
}

const reservedFields = new Set([
  ...parameterKeys, "prompt", "image", "images", "image_ids", "source_order", "mask",
  "stream", "partial_images", "user", "api_key", "API_KEY", "base_url", "headers",
  "extra_headers", "extra_query", "auth_file", "out_dir", "output_dir", "filename_prefix",
]);

export function resolveParameters(draft: ParameterDraft, config: AppConfig | null, mode: AppMode) {
  const errors: Record<string, string> = {};
  const values = Object.fromEntries(parameterKeys.map(key => [key, draft[key].trim()])) as ParameterDraft;
  const options: ImageOptions = {
    size: values.size, quality: values.quality, output_format: values.output_format, n: Number(values.n),
  };
  if (values.size !== "auto" && !/^[1-9]\d*x[1-9]\d*$/.test(values.size)) {
    errors.size = "请输入 auto 或宽x高，例如 1536x864。";
  }
  if (!values.quality) errors.quality = "请选择或输入质量。";
  if (!["png", "jpeg", "webp"].includes(values.output_format)) {
    errors.output_format = "本地图片保存支持 png、jpeg、webp。";
  }
  if (!/^\d+$/.test(values.n) || !Number.isSafeInteger(options.n) || options.n < 1 || options.n > (config?.max_n ?? 2)) {
    errors.n = `请输入 1–${config?.max_n ?? 2} 的整数，超限值不会自动修改。`;
  }
  for (const key of ["model", "background", "moderation", "response_format"] as const) {
    if (values[key]) options[key] = values[key];
  }
  if (values.moderation === "none") errors.moderation = "原 none 表示不发送；请选择服务默认。";
  if (values.background === "transparent" && values.output_format === "jpeg") {
    errors.background = "JPEG 不支持透明背景，请改用 PNG / WebP 或修改背景。";
  }
  if (values.output_format !== "png" && values.output_compression) {
    const compression = Number(values.output_compression);
    if (!/^\d+$/.test(values.output_compression) || !Number.isInteger(compression) || compression < 0 || compression > 100) {
      errors.output_compression = "请输入 0–100 的整数，或留空使用服务默认。";
    } else options.output_compression = compression;
  }
  if (mode === "edit" && values.input_fidelity) options.input_fidelity = values.input_fidelity;
  if (mode === "generate" && values.style) options.style = values.style;
  if (values.timeout) {
    const timeout = Number(values.timeout);
    if (!/^\d+(\.\d+)?$/.test(values.timeout) || !Number.isFinite(timeout) || timeout <= 0) {
      errors.timeout = "请输入正数秒数，或留空使用默认值。";
    } else options.timeout = timeout;
  }
  try {
    const extra: unknown = JSON.parse(values.extra_body);
    if (!extra || typeof extra !== "object" || Array.isArray(extra)) errors.extra_body = "扩展参数必须是 JSON 对象。";
    else {
      const conflict = Object.keys(extra).find(key => reservedFields.has(key));
      if (conflict) errors.extra_body = `“${conflict}”请在对应控件或后端配置中编辑。`;
      else if (Object.keys(extra).length) options.extra_body = extra as Record<string, unknown>;
    }
  } catch { errors.extra_body = "JSON 格式有误，请检查括号、引号与逗号。"; }
  return { options, errors };
}

export function validateDraft(draft: PromptDraft, config: AppConfig | null, mode: AppMode) {
  const result = resolveParameters(draft.options, config, mode);
  if (!draft.prompt.trim()) result.errors.prompt = "请先输入提示词或编辑指令。";
  else if ([...draft.prompt].length > (config?.max_prompt_length ?? 32000)) {
    result.errors.prompt = `提示词不能超过 ${config?.max_prompt_length ?? 32000} 字符。`;
  }
  return result;
}
