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
  "default_model": "gpt-image-1",
  "models": ["gpt-image-1"],
  "sizes": ["1024x1024", "1024x1536", "1536x1024"],
  "qualities": ["auto", "low", "medium", "high"],
  "formats": ["png", "jpeg", "webp"],
  "backgrounds": ["auto", "transparent", "opaque"],
  "max_n": 2
}
```

Must not include:

- API key
- upstream base URL
- raw `auth.json`

## `POST /api/generate`

Request:

```json
{
  "prompt": "A simple red apple on a white background",
  "options": {
    "model": "gpt-image-1",
    "size": "1024x1024",
    "quality": "low",
    "output_format": "png",
    "background": "auto",
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
      "model": "gpt-image-1",
      "size": "1024x1024",
      "quality": "low",
      "format": "png",
      "created_at": "2026-07-02T23:30:15+08:00"
    }
  ]
}
```

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
      "model": "gpt-image-1",
      "size": "1024x1024",
      "quality": "low",
      "format": "png",
      "created_at": "2026-07-02T23:30:15+08:00"
    }
  ]
}
```

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
    "model": "gpt-image-1",
    "size": "1024x1024",
    "quality": "low",
    "format": "png",
    "created_at": "2026-07-02T23:30:15+08:00",
    "revised_prompt": null
  }
]
```

Optional fields:

- `revised_prompt`

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

## Post-MVP API

These endpoints are intentionally outside MVP:

- `POST /api/edit`
- `GET /api/images/{image_id}`
- `DELETE /api/images/{image_id}`

Post-MVP edit requests should use `multipart/form-data` with `prompt`, `image`,
optional `mask`, and the same image options used by generation.
