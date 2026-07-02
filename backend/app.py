from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import OUTPUTS_DIR, get_safe_config
from .image_service import generate_images, get_images
from .schemas import (
    AppError,
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    ImageListResponse,
    SafeConfigResponse,
)


app = FastAPI(title="GPT Image WebUI Backend", version="0.1.0")

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


@app.get(
    "/api/images",
    response_model=ImageListResponse,
    response_model_exclude_none=True,
)
def images() -> ImageListResponse:
    return get_images()
