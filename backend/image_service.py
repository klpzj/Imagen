from __future__ import annotations

from datetime import datetime

from gpt_image_client import GPTImageClient

from .config import DEFAULT_MODEL, MAX_N, MODELS, get_backend_settings
from .image_store import add_records, build_record_id, list_images
from .schemas import AppError, GenerateRequest, GenerateResponse, ImageListResponse, ImageRecord


def generate_images(request: GenerateRequest) -> GenerateResponse:
    settings = get_backend_settings()
    if not settings.api_key:
        raise AppError("Image API credentials are not configured.", "auth_missing", 500)

    options = request.options
    if options.n > MAX_N:
        raise AppError(f"At most {MAX_N} images can be generated at once.", "invalid_request", 400)

    default_model = settings.default_model if settings.default_model in MODELS else DEFAULT_MODEL
    model = options.model or default_model
    created_at = datetime.now().astimezone()

    try:
        client = GPTImageClient(
            api_key=settings.api_key,
            auth_file=settings.auth_path,
            model=model,
            base_url=settings.base_url,
        )
        results = client.generate(
            request.prompt,
            out_dir=settings.outputs_dir,
            n=options.n,
            size=options.size,
            quality=options.quality,
            output_format=options.output_format,
            background=options.background,
        )
    except ValueError as exc:
        raise AppError(str(exc), "invalid_request", 400) from exc
    except Exception as exc:
        raise AppError("Generation failed.", "generation_failed", 502) from exc

    existing_ids: set[str] = set()
    records: list[ImageRecord] = []
    created_at_text = created_at.isoformat(timespec="seconds")

    for fallback_index, result in enumerate(results, start=1):
        index = result.index or fallback_index
        record_id = build_record_id(created_at, index, existing_ids)
        existing_ids.add(record_id)
        filename = result.path.name
        records.append(
            ImageRecord(
                id=record_id,
                type="generate",
                filename=filename,
                url=f"/outputs/{filename}",
                prompt=request.prompt,
                model=model,
                size=options.size,
                quality=options.quality,
                format=options.output_format,
                created_at=created_at_text,
                revised_prompt=result.revised_prompt,
            )
        )

    return GenerateResponse(images=add_records(records))


def get_images() -> ImageListResponse:
    return ImageListResponse(images=list_images())
