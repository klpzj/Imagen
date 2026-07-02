from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, validator

from .config import BACKGROUNDS, MAX_N, MODELS, OUTPUT_FORMATS, QUALITIES, SIZES


class AppError(Exception):
    def __init__(self, message: str, code: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class ErrorDetail(BaseModel):
    message: str
    code: str


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
    max_n: int


class ImageOptions(BaseModel):
    model: str | None = None
    size: str = "1024x1024"
    quality: str = "auto"
    output_format: str = "png"
    background: str | None = None
    n: int = Field(default=1, ge=1, le=MAX_N)

    @validator("model")
    def validate_model(cls, value: str | None) -> str | None:
        if value is not None and value not in MODELS:
            raise ValueError("Unsupported model.")
        return value

    @validator("size")
    def validate_size(cls, value: str) -> str:
        if value not in SIZES:
            raise ValueError("Unsupported size.")
        return value

    @validator("quality")
    def validate_quality(cls, value: str) -> str:
        if value not in QUALITIES:
            raise ValueError("Unsupported quality.")
        return value

    @validator("output_format")
    def validate_output_format(cls, value: str) -> str:
        if value not in OUTPUT_FORMATS:
            raise ValueError("Unsupported output format.")
        return value

    @validator("background")
    def validate_background(cls, value: str | None) -> str | None:
        if value is not None and value not in BACKGROUNDS:
            raise ValueError("Unsupported background.")
        return value


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    options: ImageOptions = Field(default_factory=ImageOptions)

    @validator("prompt")
    def validate_prompt(cls, value: str) -> str:
        prompt = value.strip()
        if not prompt:
            raise ValueError("Prompt cannot be empty.")
        return prompt


class ImageRecord(BaseModel):
    id: str
    type: Literal["generate"]
    filename: str
    url: str
    prompt: str
    model: str
    size: str
    quality: str
    format: str
    created_at: str
    revised_prompt: str | None = None


class GenerateResponse(BaseModel):
    images: list[ImageRecord]


class ImageListResponse(BaseModel):
    images: list[ImageRecord]
