from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import OUTPUTS_DIR, get_safe_config
from .image_service import delete_image, edit_images, generate_images, get_images
from .job_store import create_generation_job, get_active_job, get_job, list_jobs, run_generation_job
from .schemas import (
    AppError,
    EditOptions,
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


def _error_response(message: str, code: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": {"message": message, "code": code}},
    )


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return _error_response(exc.message, exc.code, exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _error_response("Invalid request.", "invalid_request", 422)


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

    options = EditOptions(
        model=model or None,
        size=size,
        quality=quality,
        output_format=output_format,
        n=n,
    )

    return edit_images(
        prompt=prompt,
        options=options,
        uploaded_images=normalized_uploads,
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
    background_tasks.add_task(run_generation_job, job.id, request)
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
