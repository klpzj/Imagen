from __future__ import annotations

import json
from fastapi import BackgroundTasks, FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .config import OUTPUTS_DIR, get_safe_config
from .image_service import delete_image, edit_images, generate_images, get_images
from .job_store import (
    create_generation_job,
    delete_job,
    get_active_job,
    get_job,
    list_jobs,
    run_generation_job,
)
from .schemas import (
    AppError,
    EditOptions,
    EditRequest,
    EditResponse,
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    ImageListResponse,
    JobListResponse,
    JobResponse,
    SafeConfigResponse,
)


app = FastAPI(title="GPT Image WebUI Backend", version="0.1.0")
ALLOWED_UPLOAD_TYPES = {"image/png", "image/jpeg", "image/webp"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")


def _error_response(
    message: str, code: str, status_code: int, fields: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": {"message": message, "code": code, "fields": fields or {}}},
    )


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return _error_response(exc.message, exc.code, exc.status_code, exc.fields)


@app.exception_handler(RequestValidationError)
@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError | ValidationError) -> JSONResponse:
    fields: dict[str, str] = {}
    for error in exc.errors():
        location = [str(part) for part in error["loc"] if part not in {"body", "options"}]
        key = location[0] if location else "options"
        fields[key] = error["msg"].removeprefix("Value error, ")
    return _error_response("请检查标出的参数。", "invalid_request", 422, fields)


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error_response("Internal server error.", "internal_error", 500)


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(ok=True)


@app.get("/api/config", response_model=SafeConfigResponse)
def config() -> dict[str, object]:
    return get_safe_config()


@app.post(
    "/api/generate",
    response_model=GenerateResponse,
    response_model_exclude_none=True,
)
def generate(request: GenerateRequest) -> GenerateResponse:
    return generate_images(request)


@app.post(
    "/api/edit",
    response_model=EditResponse,
    response_model_exclude_none=True,
)
def edit(
    prompt: str = Form(...),
    model: str | None = Form(default=None),
    size: str = Form(default="1024x1024"),
    quality: str = Form(default="auto"),
    output_format: str = Form(default="png"),
    moderation: str | None = Form(default=None),
    background: str | None = Form(default=None),
    output_compression: int | None = Form(default=None),
    input_fidelity: str | None = Form(default=None),
    response_format: str | None = Form(default=None),
    timeout: float | None = Form(default=None),
    extra_body: str = Form(default="{}"),
    mask: UploadFile | None = File(default=None),
    n: int = Form(default=1),
    images: list[UploadFile] | None = File(default=None),
    upload_ids: list[str] | None = Form(default=None),
    image_ids: list[str] | None = Form(default=None),
    source_order: list[str] | None = Form(default=None),
) -> EditResponse:
    upload_files = images or []
    upload_id_values = upload_ids or []
    normalized_uploads = []

    for index, upload in enumerate(upload_files):
        if upload.content_type not in ALLOWED_UPLOAD_TYPES:
            raise AppError("Only PNG, JPEG, and WebP images can be uploaded.", "invalid_upload", 400)
        upload_id = upload_id_values[index] if index < len(upload_id_values) else f"upload-{index + 1}"
        normalized_uploads.append((upload_id, upload.filename or f"upload-{index + 1}.png", upload.file))

    options_data = {
        "model": model or None, "size": size, "quality": quality,
        "output_format": output_format, "moderation": moderation,
        "background": background, "output_compression": output_compression,
        "input_fidelity": input_fidelity, "response_format": response_format,
        "timeout": timeout, "n": n,
    }
    try:
        options_data["extra_body"] = json.loads(extra_body)
    except (ValueError, TypeError) as exc:
        raise AppError("扩展参数 JSON 格式有误。", "invalid_request", 422,
                       {"extra_body": "请输入有效的 JSON 对象。"}) from exc
    request = EditRequest(prompt=prompt, options=EditOptions(**options_data))
    if mask and mask.content_type != "image/png":
        raise AppError("蒙版必须是 PNG 图片。", "invalid_upload", 400,
                       {"mask": "请选择包含透明通道的 PNG 蒙版。"})

    return edit_images(
        prompt=request.prompt,
        options=request.options,
        uploaded_images=normalized_uploads,
        uploaded_mask=(mask.filename or "mask.png", mask.file) if mask else None,
        image_ids=[image_id for image_id in (image_ids or []) if image_id],
        source_order=[source for source in (source_order or []) if source],
    )


@app.post(
    "/api/jobs",
    response_model=JobResponse,
    response_model_exclude_none=True,
)
def create_job(request: GenerateRequest, background_tasks: BackgroundTasks) -> JobResponse:
    job = create_generation_job(request)
    background_tasks.add_task(run_generation_job, job.id)
    return JobResponse(job=job)


@app.get(
    "/api/jobs",
    response_model=JobListResponse,
    response_model_exclude_none=True,
)
def jobs() -> JobListResponse:
    return JobListResponse(jobs=list_jobs())


@app.get(
    "/api/jobs/active",
    response_model=JobResponse,
    response_model_exclude_none=True,
)
def active_job() -> JobResponse:
    return JobResponse(job=get_active_job())


@app.get(
    "/api/jobs/{job_id}",
    response_model=JobResponse,
    response_model_exclude_none=True,
)
def job(job_id: str) -> JobResponse:
    return JobResponse(job=get_job(job_id))


@app.delete(
    "/api/jobs/{job_id}",
    response_model=JobListResponse,
    response_model_exclude_none=True,
)
def remove_job(job_id: str) -> JobListResponse:
    return JobListResponse(jobs=delete_job(job_id))


@app.get(
    "/api/images",
    response_model=ImageListResponse,
    response_model_exclude_none=True,
)
def images() -> ImageListResponse:
    return get_images()


@app.delete(
    "/api/images/{image_id}",
    response_model=ImageListResponse,
    response_model_exclude_none=True,
)
def remove_image(image_id: str) -> ImageListResponse:
    return delete_image(image_id)
