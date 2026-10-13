from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import BinaryIO

from PIL import Image, UnidentifiedImageError
from gpt_image_client import GPTImageClient

from .config import get_backend_settings
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
_LOGGER = logging.getLogger(__name__)
_MAX_UPSTREAM_ERROR_LENGTH = 1200


def _clean_error_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None

    message = " ".join(value.split())
    if not message:
        return None

    if len(message) > _MAX_UPSTREAM_ERROR_LENGTH:
        return f"{message[:_MAX_UPSTREAM_ERROR_LENGTH].rstrip()}..."

    return message


def _error_message_from_payload(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None

    error = payload.get("error", payload)
    if isinstance(error, dict):
        message = _clean_error_text(error.get("message"))
        code = _clean_error_text(error.get("code"))
        if message and code and code not in message:
            return f"{message} ({code})"
        return message

    return _clean_error_text(payload.get("message"))


def _upstream_error_message(exc: Exception, fallback: str) -> str:
    message = _error_message_from_payload(getattr(exc, "body", None))
    if message:
        return message

    response = getattr(exc, "response", None)
    if response is not None:
        try:
            message = _error_message_from_payload(response.json())
        except Exception:
            message = None
        if message:
            return message

        text = _clean_error_text(getattr(response, "text", None))
        if text:
            return text

    for attr in ("message", "user_message"):
        message = _clean_error_text(getattr(exc, attr, None))
        if message:
            return message

    return _clean_error_text(str(exc)) or fallback


def _upstream_error_fields(exc: Exception) -> dict[str, str]:
    payload = getattr(exc, "body", None)
    error = payload.get("error", payload) if isinstance(payload, dict) else None
    if isinstance(error, dict) and isinstance(error.get("param"), str):
        return {error["param"]: _upstream_error_message(exc, "参数被图像服务拒绝。")}
    return {}


def generate_images(request: GenerateRequest) -> GenerateResponse:
    settings = get_backend_settings()
    if not settings.api_key:
        raise AppError("Image API credentials are not configured.", "auth_missing", 500)

    options = request.options
    model = options.model or settings.default_model
    created_at = datetime.now().astimezone()

    try:
        client = GPTImageClient(
            api_key=settings.api_key,
            auth_file=settings.auth_path,
            model=model,
            base_url=settings.base_url,
            timeout=options.timeout,
        )
        results = client.generate(
            request.prompt,
            out_dir=settings.outputs_dir,
            **options.client_options(),
        )
    except ValueError as exc:
        raise AppError(str(exc), "invalid_request", 400) from exc
    except Exception as exc:
        message = _upstream_error_message(exc, "Generation failed.")
        _LOGGER.exception("Image generation failed: %s", message)
        raise AppError(message, "generation_failed", 502, _upstream_error_fields(exc)) from exc

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
                format="jpeg" if result.path.suffix == ".jpg" else result.path.suffix.lstrip("."),
                moderation=options.moderation,
                created_at=created_at_text,
                revised_prompt=result.revised_prompt,
                options={**options.effective_options(), "model": model},
            )
        )

    return GenerateResponse(images=add_records(records))


def edit_images(
    *,
    prompt: str,
    options: EditOptions,
    uploaded_images: list[UploadedImage] | None = None,
    uploaded_mask: tuple[str, BinaryIO] | None = None,
    image_ids: list[str] | None = None,
    source_order: list[str] | None = None,
) -> EditResponse:
    settings = get_backend_settings()
    if not settings.api_key:
        raise AppError("Image API credentials are not configured.", "auth_missing", 500)

    edit_prompt = prompt.strip()
    if not edit_prompt:
        raise AppError("Prompt cannot be empty.", "invalid_request", 400)

    uploaded_images = uploaded_images or []
    image_ids = image_ids or []
    source_order = [item for item in (source_order or []) if item]

    if not uploaded_images and not image_ids:
        raise AppError("At least one input image is required.", "invalid_request", 400)

    model = options.model or settings.default_model
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
            _inspect_image(temp_path, "images")
            upload_paths[upload_id] = temp_path
            upload_names[upload_id] = filename or temp_path.name

        history_paths: dict[str, Path] = {}
        history_names: dict[str, str] = {}
        for image_id in image_ids:
            record = get_record(image_id)
            path = _record_file_path(record.filename, settings.outputs_dir)
            history_paths[image_id] = path
            history_names[image_id] = record.filename

        input_paths, source_history_ids, source_filenames, resolved_order = _ordered_edit_sources(
            upload_paths=upload_paths,
            upload_names=upload_names,
            history_paths=history_paths,
            history_names=history_names,
            source_order=source_order,
        )

        if not input_paths:
            raise AppError("At least one valid input image is required.", "invalid_request", 400)

        mask_path = None
        if uploaded_mask:
            mask_path = temp_root / "mask.png"
            uploaded_mask[1].seek(0)
            with mask_path.open("wb") as handle:
                shutil.copyfileobj(uploaded_mask[1], handle)
            _validate_mask(mask_path, input_paths[0])

        try:
            client = GPTImageClient(
                api_key=settings.api_key,
                auth_file=settings.auth_path,
                model=model,
                base_url=settings.base_url,
                timeout=options.timeout,
            )
            results = client.edit(
                edit_prompt,
                images=input_paths,
                mask=mask_path,
                out_dir=settings.outputs_dir,
                **options.client_options(),
            )
        except ValueError as exc:
            raise AppError(str(exc), "invalid_request", 400) from exc
        except FileNotFoundError as exc:
            raise AppError(f"Input image was not found: {exc}", "image_not_found", 404) from exc
        except Exception as exc:
            message = _upstream_error_message(exc, "Edit failed.")
            _LOGGER.exception("Image edit failed: %s", message)
            raise AppError(message, "edit_failed", 502, _upstream_error_fields(exc)) from exc

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
                format="jpeg" if result.path.suffix == ".jpg" else result.path.suffix.lstrip("."),
                moderation=options.moderation,
                created_at=created_at_text,
                revised_prompt=result.revised_prompt,
                source_image_ids=source_history_ids or None,
                source_filenames=source_filenames or None,
                source_order=resolved_order,
                mask_filename=uploaded_mask[0] if uploaded_mask else None,
                options={**options.effective_options(), "model": model},
            )
        )

    return EditResponse(images=add_records(records))


def _safe_image_suffix(filename: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        return suffix
    return ".png"


def _inspect_image(path: Path, field: str) -> tuple[int, int]:
    try:
        with Image.open(path) as image:
            if image.format not in {"PNG", "JPEG", "WEBP"}:
                raise ValueError("不支持的图片格式。")
            dimensions = image.size
            image.verify()
            return dimensions
    except (OSError, ValueError, UnidentifiedImageError) as exc:
        raise AppError("图片无法读取，请检查上传文件。", "invalid_upload", 400,
                       {field: "请上传有效的 PNG、JPEG 或 WebP 图片。"}) from exc


def _validate_mask(path: Path, source: Path) -> None:
    if path.stat().st_size >= 4 * 1024 * 1024:
        raise AppError("蒙版需小于 4 MB。", "invalid_mask", 400, {"mask": "请选择小于 4 MB 的 PNG 蒙版。"})
    dimensions = _inspect_image(path, "mask")
    with Image.open(path) as image:
        has_alpha = "A" in image.getbands() or "transparency" in image.info
        if image.format != "PNG" or not has_alpha:
            raise AppError("蒙版需要 PNG 透明通道。", "invalid_mask", 400,
                           {"mask": "使用透明区域指定编辑范围。"})
    if dimensions != _inspect_image(source, "images"):
        raise AppError("蒙版尺寸与第一张输入图不一致。", "invalid_mask", 400,
                       {"mask": "请选择与第一张输入图相同尺寸的蒙版。"})


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
) -> tuple[list[Path], list[str], list[str], list[str]]:
    input_paths: list[Path] = []
    source_history_ids: list[str] = []
    source_filenames: list[str] = []
    resolved_order: list[str] = []
    used_uploads: set[str] = set()
    used_history: set[str] = set()

    def add_upload(upload_id: str) -> None:
        if upload_id in used_uploads or upload_id not in upload_paths:
            return
        used_uploads.add(upload_id)
        input_paths.append(upload_paths[upload_id])
        source_filenames.append(upload_names[upload_id])
        resolved_order.append(f"upload:{upload_names[upload_id]}")

    def add_history(image_id: str) -> None:
        if image_id in used_history or image_id not in history_paths:
            return
        used_history.add(image_id)
        input_paths.append(history_paths[image_id])
        source_history_ids.append(image_id)
        source_filenames.append(history_names[image_id])
        resolved_order.append(f"history:{image_id}")

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

    return input_paths, source_history_ids, source_filenames, resolved_order


def get_images() -> ImageListResponse:
    return ImageListResponse(images=list_images())


def delete_image(image_id: str) -> ImageListResponse:
    return ImageListResponse(images=delete_record(image_id))
