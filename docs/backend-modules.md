# Backend Modules

The backend should be a small FastAPI service that exposes local HTTP routes for
the Vue app and keeps secrets out of the browser.

## `backend/app.py`

Responsibilities:

- Create the FastAPI app.
- Configure CORS for the Vite dev server.
- Register API routes.
- Serve files from `outputs/`.
- Convert unhandled exceptions into readable API errors.

Current routes:

```text
GET    /api/health
GET    /api/config
POST   /api/generate
POST   /api/edit
POST   /api/jobs
GET    /api/jobs
GET    /api/jobs/active
GET    /api/jobs/{job_id}
GET    /api/images
DELETE /api/images/{image_id}
```

Static files:

```text
/outputs/{filename} -> outputs/{filename}
```

## `backend/config.py`

Responsibilities:

- Resolve project paths.
- Read `auth.json`.
- Provide backend-only config:
  - API key
  - upstream base URL
  - default image model
- Provide browser-safe config:
  - available models
  - available sizes
  - quality choices
  - output formats
  - moderation choices
  - legacy background choices

Safe response example:

```json
{
  "default_model": "gpt-image-2",
  "models": ["gpt-image-2", "gpt-image-1", "gpt-image-1-mini"],
  "sizes": ["1024x1024", "1024x1536", "1536x1024"],
  "qualities": ["auto", "low", "medium", "high"],
  "formats": ["png", "jpeg", "webp"],
  "backgrounds": ["auto", "transparent", "opaque"],
  "moderations": ["none", "auto", "low"],
  "max_n": 2
}
```

The API key must never be included in this response.

## `backend/schemas.py`

Responsibilities:

- Define request and response models with Pydantic.
- Keep frontend and backend contracts explicit.
- Centralize validation constraints.

Planned models:

```python
class ImageOptions(BaseModel):
    model: str | None = None
    size: str = "1024x1024"
    quality: str = "auto"
    output_format: str = "png"
    background: str | None = None
    moderation: str = "none"
    n: int = 1

class GenerateRequest(BaseModel):
    prompt: str
    options: ImageOptions

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

class GenerateResponse(BaseModel):
    images: list[ImageRecord]
```

## `backend/image_service.py`

Responsibilities:

- Validate user-level generation requests.
- Build calls to `GPTImageClient`.
- Normalize client results into `ImageRecord` objects.
- Register records through `image_store.py`.

Generate flow:

```text
GenerateRequest
  -> validate prompt/options
  -> GPTImageClient.generate
  -> create ImageRecord entries
  -> image_store.add_records
  -> GenerateResponse
```

Generated files should remain under:

```text
outputs/
```

Edit flow:

```text
multipart form-data
  -> stage uploads in a temporary outputs/ directory
  -> GPTImageClient.edit
  -> create ImageRecord entries
  -> image_store.add_records
  -> EditResponse
```

## `backend/image_store.py`

Responsibilities:

- Read and write `outputs/manifest.json`.
- Create stable IDs.
- List, add, get, and delete image records.
- Remove local image files when deleting history records.

Public functions:

```python
def list_images() -> list[ImageRecord]: ...
def add_records(records: list[ImageRecord]) -> list[ImageRecord]: ...
def get_record(image_id: str) -> ImageRecord | None: ...
def delete_record(image_id: str) -> list[ImageRecord]: ...
```

Write behavior:

- Ensure `outputs/` exists.
- If `manifest.json` does not exist, treat it as an empty list.
- Write manifest atomically through a temporary file then replace.
- Sort records newest first for API responses.

## `backend/job_store.py`

Responsibilities:

- Read and write `outputs/jobs.json`.
- Persist queued, running, succeeded, and failed generation tasks.
- Keep only the newest bounded set of jobs.
- Expose the active queued/running task for frontend refresh recovery.

Public functions:

```python
def create_generation_job(request: GenerateRequest) -> GenerationJob: ...
def run_generation_job(job_id: str, request: GenerateRequest) -> None: ...
def list_jobs() -> list[GenerationJob]: ...
def get_job(job_id: str) -> GenerationJob | None: ...
def get_active_job() -> GenerationJob | None: ...
```

## Error Shape

All API errors should use a consistent JSON shape:

```json
{
  "detail": {
    "message": "Generation failed",
    "code": "generation_failed"
  }
}
```

Common codes:

- `invalid_request`
- `auth_missing`
- `upstream_error`
- `generation_failed`
- `edit_failed`
- `image_not_found`
- `jobs_invalid`

## Backend Dependencies

Add to `requirements.txt`:

```text
fastapi
uvicorn[standard]
python-multipart
pydantic
```
