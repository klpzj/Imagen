from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from .config import JOBS_PATH, OUTPUTS_DIR
from .image_service import generate_images
from .schemas import AppError, GenerateRequest, GenerationJob


_LOCK = threading.Lock()
_ACTIVE_STATUSES = {"queued", "running"}


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _model_to_data(model: object) -> dict[str, object]:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_none=False)  # type: ignore[attr-defined]
    if hasattr(model, "dict"):
        return model.dict(exclude_none=False)  # type: ignore[attr-defined]
    raise TypeError(f"Unsupported model object: {type(model)!r}")


def _job_from_data(data: dict[str, object]) -> GenerationJob:
    if hasattr(GenerationJob, "model_validate"):
        return GenerationJob.model_validate(data)
    return GenerationJob.parse_obj(data)


def _job_to_data(job: GenerationJob) -> dict[str, object]:
    return _model_to_data(job)


def _ensure_outputs_dir() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


def _read_jobs(path: Path = JOBS_PATH) -> list[GenerationJob]:
    _ensure_outputs_dir()
    if not path.is_file():
        return []

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise AppError("Job store is not valid JSON.", "jobs_invalid", 500) from exc

    if not isinstance(data, list):
        raise AppError("Job store must contain a list.", "jobs_invalid", 500)

    return [_job_from_data(item) for item in data if isinstance(item, dict)]


def _write_jobs(jobs: list[GenerationJob], path: Path = JOBS_PATH) -> None:
    _ensure_outputs_dir()
    jobs = sorted(jobs, key=lambda job: (job.created_at, job.id), reverse=True)
    payload = [_job_to_data(job) for job in jobs[:80]]
    tmp_path = path.with_suffix(".json.tmp")

    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    os.replace(tmp_path, path)


def _replace_job(updated: GenerationJob) -> GenerationJob:
    with _LOCK:
        jobs = _read_jobs()
        next_jobs = [job for job in jobs if job.id != updated.id]
        next_jobs.append(updated)
        _write_jobs(next_jobs)
    return updated


def list_jobs() -> list[GenerationJob]:
    with _LOCK:
        return _read_jobs()


def get_job(job_id: str) -> GenerationJob:
    with _LOCK:
        job = next((item for item in _read_jobs() if item.id == job_id), None)

    if job is None:
        raise AppError("Generation job was not found.", "job_not_found", 404)

    return job


def get_active_job() -> GenerationJob | None:
    jobs = list_jobs()
    return next((job for job in jobs if job.status in _ACTIVE_STATUSES), None)


def delete_job(job_id: str) -> list[GenerationJob]:
    with _LOCK:
        jobs = _read_jobs()
        job = next((item for item in jobs if item.id == job_id), None)

        if job is None:
            raise AppError("Generation job was not found.", "job_not_found", 404)

        if job.status != "failed":
            raise AppError(
                "Only failed generation jobs can be deleted.",
                "job_delete_not_allowed",
                400,
            )

        next_jobs = [item for item in jobs if item.id != job_id]
        _write_jobs(next_jobs)
        return next_jobs


def create_generation_job(request: GenerateRequest) -> GenerationJob:
    created_at = _now()
    job = GenerationJob(
        id=f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}",
        status="queued",
        prompt=request.prompt,
        options=_model_to_data(request.options),
        created_at=created_at,
        updated_at=created_at,
    )
    _replace_job(job)
    return job


def run_generation_job(job_id: str, request: GenerateRequest) -> None:
    job = get_job(job_id)
    _replace_job(job.copy(update={"status": "running", "updated_at": _now()}))

    try:
        response = generate_images(request)
    except Exception as exc:
        message = exc.message if isinstance(exc, AppError) else "Generation failed."
        failed = get_job(job_id).copy(
            update={
                "status": "failed",
                "updated_at": _now(),
                "error": message,
            }
        )
        _replace_job(failed)
        return

    done = get_job(job_id).copy(
        update={
            "status": "succeeded",
            "updated_at": _now(),
            "images": response.images,
            "error": None,
        }
    )
    _replace_job(done)
