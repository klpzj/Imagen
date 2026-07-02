from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import MANIFEST_PATH, OUTPUTS_DIR
from .schemas import AppError, ImageRecord


def _record_from_data(data: dict[str, Any]) -> ImageRecord:
    if hasattr(ImageRecord, "model_validate"):
        return ImageRecord.model_validate(data)
    return ImageRecord.parse_obj(data)


def _record_to_data(record: ImageRecord) -> dict[str, Any]:
    if hasattr(record, "model_dump"):
        return record.model_dump(exclude_none=False)
    return record.dict(exclude_none=False)


def _sort_records(records: list[ImageRecord]) -> list[ImageRecord]:
    return sorted(records, key=lambda record: (record.created_at, record.id), reverse=True)


def _ensure_outputs_dir() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


def _read_manifest(path: Path = MANIFEST_PATH) -> list[ImageRecord]:
    _ensure_outputs_dir()
    if not path.is_file():
        return []

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise AppError("Image manifest is not valid JSON.", "manifest_invalid", 500) from exc

    if not isinstance(data, list):
        raise AppError("Image manifest must contain a list.", "manifest_invalid", 500)

    return [_record_from_data(item) for item in data if isinstance(item, dict)]


def _write_manifest(records: list[ImageRecord], path: Path = MANIFEST_PATH) -> None:
    _ensure_outputs_dir()
    sorted_records = _sort_records(records)
    payload = [_record_to_data(record) for record in sorted_records]
    tmp_path = path.with_suffix(".json.tmp")

    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    os.replace(tmp_path, path)


def list_images() -> list[ImageRecord]:
    return _sort_records(_read_manifest())


def add_records(records: list[ImageRecord]) -> list[ImageRecord]:
    if not records:
        return []

    existing = _read_manifest()
    seen_ids = {record.id for record in existing}
    normalized: list[ImageRecord] = []

    for record in records:
        candidate = record
        if candidate.id in seen_ids:
            candidate = candidate.copy(update={"id": _next_record_id(datetime.now().astimezone(), seen_ids)})
        seen_ids.add(candidate.id)
        normalized.append(candidate)

    _write_manifest(existing + normalized)
    return normalized


def build_record_id(created_at: datetime, index: int, existing_ids: set[str] | None = None) -> str:
    existing_ids = existing_ids or {record.id for record in _read_manifest()}
    base = created_at.strftime("%Y%m%d-%H%M%S")
    candidate = f"{base}-{index}"
    if candidate not in existing_ids:
        return candidate
    return _next_record_id(created_at, existing_ids)


def _next_record_id(created_at: datetime, existing_ids: set[str]) -> str:
    base = created_at.strftime("%Y%m%d-%H%M%S")
    sequence = 1
    while f"{base}-{sequence}" in existing_ids:
        sequence += 1
    return f"{base}-{sequence}"
