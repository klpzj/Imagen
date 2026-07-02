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

MVP routes:

```text
GET    /api/health
GET    /api/config
POST   /api/generate
GET    /api/images
```

Post-MVP routes:

```text
POST   /api/edit
GET    /api/images/{image_id}
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
  - background choices

Safe response example:

```json
{
  "default_model": "gpt-image-1",
  "models": ["gpt-image-1"],
  "sizes": ["1024x1024", "1024x1536", "1536x1024"],
  "qualities": ["auto", "low", "medium", "high"],
  "formats": ["png", "jpeg", "webp"],
  "backgrounds": ["auto", "transparent", "opaque"],
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
    n: int = 1

class GenerateRequest(BaseModel):
    prompt: str
    options: ImageOptions

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

Post-MVP edit flow:

```text
multipart form-data
  -> save upload to outputs/uploads/
  -> GPTImageClient.edit
  -> create ImageRecord entries
  -> image_store.add_records
  -> EditResponse
```

## `backend/image_store.py`

Responsibilities:

- Read and write `outputs/manifest.json`.
- Create stable IDs.
- List and add image records.
- Keep deletion out of MVP to avoid accidental file loss while the manifest
  format is still settling.

Public functions:

```python
def list_images() -> list[ImageRecord]: ...
def add_records(records: list[ImageRecord]) -> list[ImageRecord]: ...
```

Post-MVP functions:

```python
def get_image(image_id: str) -> ImageRecord | None: ...
def delete_image(image_id: str) -> bool: ...
```

Write behavior:

- Ensure `outputs/` exists.
- If `manifest.json` does not exist, treat it as an empty list.
- Write manifest atomically through a temporary file then replace.
- Sort records newest first for API responses.

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

Post-MVP codes:

- `edit_failed`
- `image_not_found`

## Backend Dependencies

Add to `requirements.txt`:

```text
fastapi
uvicorn[standard]
python-multipart
pydantic
```
