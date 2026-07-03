# API And Data Contract

This document is the contract between the FastAPI backend and Vue frontend.

## Base URLs

Development:

```text
Backend: http://localhost:18000
Frontend: http://localhost:5173
```

Frontend requests use relative `/api` and `/outputs` paths by default. In local
development, the Vite dev server proxies those paths to
`http://localhost:18000`.

## `GET /api/health`

Response:

```json
{
  "ok": true
}
```

## `GET /api/config`

Returns browser-safe configuration.

Response:

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

Must not include:

- API key
- upstream base URL
- raw `auth.json`

`backgrounds` is currently returned for backend/client compatibility. The
Vue WebUI does not render background controls.

## `POST /api/generate`

Request:

```json
{
  "prompt": "A simple red apple on a white background",
  "options": {
    "model": "gpt-image-2",
    "size": "1024x1024",
    "quality": "low",
    "output_format": "png",
    "moderation": "none",
    "n": 1
  }
}
```

Response:

```json
{
  "images": [
    {
      "id": "20260702-233015-1",
      "type": "generate",
      "filename": "baseurl-test-20260702-233015-1.png",
      "url": "/outputs/baseurl-test-20260702-233015-1.png",
      "prompt": "A simple red apple on a white background",
      "model": "gpt-image-2",
      "size": "1024x1024",
      "quality": "low",
      "format": "png",
      "moderation": "none",
      "created_at": "2026-07-02T23:30:15+08:00"
    }
  ]
}
```

## `POST /api/edit`

Request uses `multipart/form-data`:

- `prompt`: edit instruction
- `images`: uploaded PNG/JPEG/WebP files, optional when `image_ids` is provided
- `image_ids`: existing history image IDs, optional when files are uploaded
- `source_order`: optional source ordering values
- `model`, `size`, `quality`, `output_format`, `moderation`, `n`: image
  options

Response shape matches `POST /api/generate`, with image records using
`type: "edit"` and optional `source_image_ids` / `source_filenames`.

## `POST /api/jobs`

Creates a persisted background generation task.

Request shape matches `POST /api/generate`.

Response:

```json
{
  "job": {
    "id": "job-20260702-233015",
    "status": "queued",
    "prompt": "A simple red apple on a white background",
    "options": {
      "model": "gpt-image-2",
      "size": "1024x1024",
      "quality": "low",
      "output_format": "png",
      "moderation": "none",
      "n": 1
    },
    "created_at": "2026-07-02T23:30:15+08:00",
    "updated_at": "2026-07-02T23:30:15+08:00",
    "images": [],
    "error": null
  }
}
```

## `GET /api/jobs`

Returns persisted jobs newest first. Failed jobs are retained with
`status: "failed"` and an `error` message.

## `GET /api/jobs/active`

Returns the newest queued or running job, or `null` when no job is active.

## `GET /api/jobs/{job_id}`

Returns one job by ID, or `null` when not found.

## `DELETE /api/jobs/{job_id}`

Deletes a failed generation job from `outputs/jobs.json`. Only failed jobs can
be deleted; queued, running, and succeeded jobs return an API error.

## `GET /api/images`

Returns newest first.

Response:

```json
{
  "images": [
    {
      "id": "20260702-233015-1",
      "type": "generate",
      "filename": "baseurl-test-20260702-233015-1.png",
      "url": "/outputs/baseurl-test-20260702-233015-1.png",
      "prompt": "A simple red apple on a white background",
      "model": "gpt-image-2",
      "size": "1024x1024",
      "quality": "low",
      "format": "png",
      "moderation": "none",
      "created_at": "2026-07-02T23:30:15+08:00"
    }
  ]
}
```

## `DELETE /api/images/{image_id}`

Deletes the manifest record and local image file when present.

Response shape matches `GET /api/images`.

## Manifest Schema

File:

```text
outputs/manifest.json
```

Shape:

```json
[
  {
    "id": "20260702-233015-1",
    "type": "generate",
    "filename": "baseurl-test-20260702-233015-1.png",
    "url": "/outputs/baseurl-test-20260702-233015-1.png",
    "prompt": "A simple red apple on a white background",
    "model": "gpt-image-2",
    "size": "1024x1024",
    "quality": "low",
    "format": "png",
    "moderation": "none",
    "created_at": "2026-07-02T23:30:15+08:00",
    "revised_prompt": null
  }
]
```

Optional fields:

- `revised_prompt`
- `moderation`
- `source_image_ids`
- `source_filenames`

## Job Store Schema

File:

```text
outputs/jobs.json
```

Shape:

```json
[
  {
    "id": "job-20260702-233015",
    "status": "succeeded",
    "prompt": "A simple red apple on a white background",
    "options": {
      "model": "gpt-image-2",
      "size": "1024x1024",
      "quality": "low",
      "output_format": "png",
      "moderation": "none",
      "n": 1
    },
    "created_at": "2026-07-02T23:30:15+08:00",
    "updated_at": "2026-07-02T23:30:25+08:00",
    "images": [],
    "error": null
  }
]
```

## Error Contract

Response:

```json
{
  "detail": {
    "message": "Generation failed",
    "code": "generation_failed"
  }
}
```

Frontend should display `detail.message`. If the shape is unknown, display a
generic error.
