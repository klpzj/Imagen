from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import BinaryIO

from gpt_image_client import GPTImageClient

from .config import DEFAULT_MODEL, MAX_N, get_backend_settings, get_model_candidates
from .image_store import add_records, build_record_id, delete_record, get_record, list_images
from .schemas import (
    AppError,
    EditOptions,
    EditResponse,
    GenerateRequest,
    GenerateResponse,
    ImageListResponse,
    ImageRecord,
)


UploadedImage = tuple[str, str, BinaryIO]


def generate_images(request: GenerateRequest) -> GenerateResponse:
    settings = get_backend_settings()
    if not settings.api_key:
        raise AppError("Image API credentials are not configured.", "auth_missing", 500)

    options = request.options
    if options.n > MAX_N:
        raise AppError(f"At most {MAX_N} images can be generated at once.", "invalid_request", 400)

    models = get_model_candidates()
    default_model = settings.default_model if settings.default_model in models else DEFAULT_MODEL
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
            moderation=options.moderation,
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
                moderation=options.moderation,
                created_at=created_at_text,
                revised_prompt=result.revised_prompt,
            )
        )

    return GenerateResponse(images=add_records(records))


def edit_images(
    *,
    prompt: str,
    options: EditOptions,
    uploaded_images: list[UploadedImage] | None = None,
    image_ids: list[str] | None = None,
    source_order: list[str] | None = None,
) -> EditResponse:
    settings = get_backend_settings()
    if not settings.api_key:
        raise AppError("Image API credentials are not configured.", "auth_missing", 500)

    edit_prompt = prompt.strip()
    if not edit_prompt:
        raise AppError("Prompt cannot be empty.", "invalid_request", 400)

    if options.n > MAX_N:
        raise AppError(f"At most {MAX_N} images can be edited at once.", "invalid_request", 400)

    uploaded_images = uploaded_images or []
    image_ids = image_ids or []
    source_order = [item for item in (source_order or []) if item]

    if not uploaded_images and not image_ids:
        raise AppError("At least one input image is required.", "invalid_request", 400)

    models = get_model_candidates()
    default_model = settings.default_model if settings.default_model in models else DEFAULT_MODEL
    model = options.model or default_model
    created_at = datetime.now().astimezone()

    with TemporaryDirectory(prefix="edit-upload-", dir=settings.outputs_dir) as temp_dir:
        temp_root = Path(temp_dir)
        upload_paths: dict[str, Path] = {}
        upload_names: dict[str, str] = {}

        for index, (upload_id, filename, stream) in enumerate(uploaded_images, start=1):
            suffix = _safe_image_suffix(filename)
            temp_path = temp_root / f"upload-{index}{suffix}"
            stream.seek(0)
            with temp_path.open("wb") as handle:
                shutil.copyfileobj(stream, handle)
            upload_paths[upload_id] = temp_path
            upload_names[upload_id] = filename or temp_path.name

        history_paths: dict[str, Path] = {}
        history_names: dict[str, str] = {}
        for image_id in image_ids:
            record = get_record(image_id)
            path = _record_file_path(record.filename, settings.outputs_dir)
            history_paths[image_id] = path
            history_names[image_id] = record.filename

        input_paths, source_history_ids, source_filenames = _ordered_edit_sources(
            upload_paths=upload_paths,
            upload_names=upload_names,
            history_paths=history_paths,
            history_names=history_names,
            source_order=source_order,
        )

        if not input_paths:
            raise AppError("At least one valid input image is required.", "invalid_request", 400)

        try:
            client = GPTImageClient(
                api_key=settings.api_key,
                auth_file=settings.auth_path,
                model=model,
                base_url=settings.base_url,
            )
            results = client.edit(
                edit_prompt,
                images=input_paths,
                out_dir=settings.outputs_dir,
                n=options.n,
                size=options.size,
                quality=options.quality,
                output_format=options.output_format,
            )
        except ValueError as exc:
            raise AppError(str(exc), "invalid_request", 400) from exc
        except FileNotFoundError as exc:
            raise AppError(f"Input image was not found: {exc}", "image_not_found", 404) from exc
        except Exception as exc:
            raise AppError("Edit failed.", "edit_failed", 502) from exc

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
                type="edit",
                filename=filename,
                url=f"/outputs/{filename}",
                prompt=edit_prompt,
                model=model,
                size=options.size,
                quality=options.quality,
                format=options.output_format,
                moderation=None,
                created_at=created_at_text,
                revised_prompt=result.revised_prompt,
                source_image_ids=source_history_ids or None,
                source_filenames=source_filenames or None,
            )
        )

    return EditResponse(images=add_records(records))


def _safe_image_suffix(filename: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        return suffix
    return ".png"


def _record_file_path(filename: str, outputs_dir: Path) -> Path:
    path = (outputs_dir / filename).resolve()
    root = outputs_dir.resolve()
    if root not in path.parents or not path.is_file():
        raise AppError("Image file was not found.", "image_not_found", 404)
    return path


def _ordered_edit_sources(
    *,
    upload_paths: dict[str, Path],
    upload_names: dict[str, str],
    history_paths: dict[str, Path],
    history_names: dict[str, str],
    source_order: list[str],
) -> tuple[list[Path], list[str], list[str]]:
    input_paths: list[Path] = []
    source_history_ids: list[str] = []
    source_filenames: list[str] = []
    used_uploads: set[str] = set()
    used_history: set[str] = set()

    def add_upload(upload_id: str) -> None:
        if upload_id in used_uploads or upload_id not in upload_paths:
            return
        used_uploads.add(upload_id)
        input_paths.append(upload_paths[upload_id])
        source_filenames.append(upload_names[upload_id])

    def add_history(image_id: str) -> None:
        if image_id in used_history or image_id not in history_paths:
            return
        used_history.add(image_id)
        input_paths.append(history_paths[image_id])
        source_history_ids.append(image_id)
        source_filenames.append(history_names[image_id])

    for source in source_order:
        kind, _, value = source.partition(":")
        if kind == "upload":
            add_upload(value)
        elif kind == "history":
            add_history(value)

    for upload_id in upload_paths:
        add_upload(upload_id)
    for image_id in history_paths:
        add_history(image_id)

    return input_paths, source_history_ids, source_filenames


def get_images() -> ImageListResponse:
    return ImageListResponse(images=list_images())


def delete_image(image_id: str) -> ImageListResponse:
    return ImageListResponse(images=delete_record(image_id))
