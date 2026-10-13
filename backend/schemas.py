from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, validator

from gpt_image_client import validate_extra_body
from .config import MAX_N, MAX_PROMPT_LENGTH, OUTPUT_FORMATS


class AppError(Exception):
    def __init__(
        self, message: str, code: str, status_code: int = 400,
        fields: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.fields = fields or {}


class ErrorDetail(BaseModel):
    message: str
    code: str
    fields: dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    detail: ErrorDetail


class HealthResponse(BaseModel):
    ok: bool


class SafeConfigResponse(BaseModel):
    default_model: str
    models: list[str]
    sizes: list[str]
    qualities: list[str]
    formats: list[str]
    backgrounds: list[str]
    moderations: list[str]
    input_fidelities: list[str]
    styles: list[str]
    response_formats: list[str]
    max_n: int
    max_prompt_length: int


class ImageOptions(BaseModel):
    model: str | None = None
    size: str = "1024x1024"
    quality: str = "auto"
    output_format: str = "png"
    background: str | None = None
    moderation: str | None = None
    n: int = Field(default=1, ge=1, le=MAX_N, strict=True)
    output_compression: int | None = Field(default=None, ge=0, le=100, strict=True)
    response_format: str | None = None
    timeout: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    extra_body: dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "forbid"

    @validator("model", "background", "moderation", "response_format", pre=True)
    def optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("请输入文本值。")
        return value.strip() or None

    @validator("moderation")
    def legacy_moderation(cls, value: str | None) -> str | None:
        # Existing API/CLI callers and stored jobs use none to omit this field.
        return None if value == "none" else value

    @validator("size", "quality", "output_format")
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("参数不能为空。")
        return value.strip()

    @validator("size")
    def validate_size(cls, value: str) -> str:
        if value != "auto" and not re.fullmatch(r"[1-9]\d*x[1-9]\d*", value):
            raise ValueError("请输入 auto 或宽x高，例如 1536x864。")
        return value

    @validator("output_format")
    def validate_output_format(cls, value: str) -> str:
        if value not in OUTPUT_FORMATS:
            raise ValueError("本地图片保存支持 png、jpeg、webp。")
        return value

    @validator("extra_body")
    def validate_extensions(cls, value: dict[str, Any]) -> dict[str, Any]:
        validate_extra_body(value)
        return value

    @validator("background")
    def validate_transparency(cls, value: str | None, values: dict[str, Any]) -> str | None:
        if value == "transparent" and values.get("output_format") == "jpeg":
            raise ValueError("JPEG 无法保存透明背景，请选择 PNG / WebP 或修改背景。")
        return value

    def effective_options(self) -> dict[str, Any]:
        values = self.dict(exclude_none=True)
        if self.output_format == "png":
            values.pop("output_compression", None)
        if not self.extra_body:
            values.pop("extra_body", None)
        return values

    def client_options(self) -> dict[str, Any]:
        return {key: value for key, value in self.effective_options().items()
                if key not in {"model", "timeout"}}


class GenerateOptions(ImageOptions):
    style: str | None = None

    @validator("style", pre=True)
    def optional_style(cls, value: str | None) -> str | None:
        return cls.optional_text(value)


class EditOptions(ImageOptions):
    input_fidelity: str | None = None

    @validator("input_fidelity", pre=True)
    def optional_fidelity(cls, value: str | None) -> str | None:
        return cls.optional_text(value)


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=MAX_PROMPT_LENGTH)
    options: GenerateOptions = Field(default_factory=GenerateOptions)

    @validator("prompt")
    def validate_prompt(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("请输入提示词或编辑指令。")
        return value.strip()


class EditRequest(GenerateRequest):
    options: EditOptions = Field(default_factory=EditOptions)


class ImageRecord(BaseModel):
    id: str
    type: Literal["generate", "edit"]
    filename: str
    url: str
    prompt: str
    model: str
    size: str
    quality: str
    format: str
    moderation: str | None = None
    created_at: str
    revised_prompt: str | None = None
    source_image_ids: list[str] | None = None
    source_filenames: list[str] | None = None
    source_order: list[str] | None = None
    mask_filename: str | None = None
    options: dict[str, Any] | None = None


class GenerateResponse(BaseModel):
    images: list[ImageRecord]


class EditResponse(BaseModel):
    images: list[ImageRecord]


class ImageListResponse(BaseModel):
    images: list[ImageRecord]


class GenerationJob(BaseModel):
    id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    prompt: str
    options: dict[str, object]
    created_at: str
    updated_at: str
    images: list[ImageRecord] = Field(default_factory=list)
    error: str | None = None
    error_fields: dict[str, str] = Field(default_factory=dict)


class JobResponse(BaseModel):
    job: GenerationJob | None = None


class JobListResponse(BaseModel):
    jobs: list[GenerationJob]
