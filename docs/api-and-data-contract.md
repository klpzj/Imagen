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
  "models": [
    "gpt-image-2",
    "gpt-image-1",
    "gpt-image-1-mini"
  ],
  "sizes": [
    "auto",
    "1024x1024",
    "1024x1536",
    "1536x1024"
  ],
  "qualities": [
    "auto",
    "low",
    "medium",
    "high"
  ],
  "formats": [
    "png",
    "jpeg",
    "webp"
  ],
  "backgrounds": [
    "auto",
    "transparent",
    "opaque"
  ],
  "moderations": [
    "auto",
    "low"
  ],
  "input_fidelities": [
    "low",
    "high"
  ],
  "styles": [
    "natural",
    "vivid"
  ],
  "response_formats": [
    "b64_json",
    "url"
  ],
  "max_n": 2,
  "max_prompt_length": 32000
}
```

Must not include:

- API key
- upstream base URL
- raw `auth.json`

These arrays provide editable suggestions. Model and quality values are not
validated against suggestion lists; the upstream service decides whether it
supports a custom value. The WebUI renders every parameter below with the same
rules for generation and editing.

## Shared image options

| Field | Contract |
| --- | --- |
| `model` | Optional text; omitted/blank selects the configured backend default |
| `size` | `auto` or positive integer `WIDTHxHEIGHT`; default `1024x1024` |
| `quality` | Non-empty text; default `auto` |
| `output_format` | `png`, `jpeg`, or `webp`; default `png` |
| `n` | Integer 1–2; default 1; rejected rather than clamped |
| `background` | Optional text; `transparent` conflicts with `jpeg` |
| `moderation` | Optional text; legacy `none` means omit, not disable moderation |
| `output_compression` | Optional integer 0–100; omitted for PNG requests |
| `response_format` | Optional text, such as `b64_json` or `url` |
| `timeout` | Optional positive finite seconds; otherwise SDK default timeout |
| `extra_body` | JSON object of additional image-body parameters; default `{}` |

Generation adds optional `style`; editing adds optional `input_fidelity`.
Unused operation-specific fields are not sent by the WebUI. JSON options reject
unknown fields. Optional blank values are omitted; `auto` is an explicit value.
Zero and false extension values are preserved. Extensions cannot override
dedicated fields, image references, stream settings, credentials, headers,
upstream addresses, or local output paths. Streaming is not exposed.

Prompts are trimmed and must contain 1–32000 characters in both modes. Upstream
models can impose further limits on prompts, dimensions, and other parameters.
Requests are not silently retried or rewritten after rejection.

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
      "created_at": "2026-07-02T23:30:15+08:00",
      "options": {
        "model": "gpt-image-2",
        "size": "1024x1024",
        "quality": "low",
        "output_format": "png",
        "n": 1
      }
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
- `upload_ids`: identifiers paired with uploaded `images`
- All shared options above, plus `input_fidelity`; numbers use form text and
  `extra_body` uses JSON object text
- `mask`: optional PNG file with an alpha channel, smaller than 4 MB and the
  same dimensions as the first ordered input image

`source_order` entries use `upload:<upload_id>` or `history:<image_id>`. With no
ordering supplied, uploaded inputs precede history inputs. The backend validates
the actual file content before calling the image service. Edits remain synchronous.

Response shape matches `POST /api/generate`, with image records using
`type: "edit"` and optional `source_image_ids` / `source_filenames`.

## `POST /api/jobs`

Creates a persisted background generation task.

Request shape matches `POST /api/generate`.

Only one persisted generation job can be queued/running at a time; another
submission returns `409` with `job_busy`. Each job stores a complete effective
request, including the resolved default model. The worker executes that persisted
snapshot rather than mutable browser state. Omitted options and PNG compression
are excluded. `timeout` is retained as a client setting, not sent in the API body.

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
      "n": 1
    },
    "created_at": "2026-07-02T23:30:15+08:00",
    "updated_at": "2026-07-02T23:30:15+08:00",
    "images": [],
    "error": null,
    "error_fields": {}
  }
}
```

## `GET /api/jobs`

Returns persisted jobs newest first. Failed jobs are retained with
`status: "failed"` and an `error` message.

## `GET /api/jobs/active`

Returns the newest queued or running job, or `null` when no job is active.

## `GET /api/jobs/{job_id}`

Returns one job by ID, or `404` with `job_not_found` when not found.

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
      "created_at": "2026-07-02T23:30:15+08:00",
      "options": {
        "model": "gpt-image-2",
        "size": "1024x1024",
        "quality": "low",
        "output_format": "png",
        "n": 1
      }
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
    "created_at": "2026-07-02T23:30:15+08:00",
    "revised_prompt": null,
    "options": {
      "model": "gpt-image-2",
      "size": "1024x1024",
      "quality": "low",
      "output_format": "png",
      "n": 1
    }
  }
]
```

Optional fields:

- `revised_prompt`
- `moderation`
- `source_image_ids`
- `source_filenames`
- `options`: complete effective request options, including resolved model;
  absent on older records
- `source_order`: edit sources in actual request order, represented as
  `history:<image_id>` or `upload:<original_filename>`; uploaded files themselves
  are not retained
- `mask_filename`: original uploaded mask filename, when used

Record `format` and file suffix describe actual returned image bytes. The
requested output format remains in `options.output_format`. PNG, JPEG, and WebP
are inspected before saving; filenames distinguish separate request batches.

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
      "n": 1
    },
    "created_at": "2026-07-02T23:30:15+08:00",
    "updated_at": "2026-07-02T23:30:25+08:00",
    "images": [],
    "error": null,
    "error_fields": {}
  }
]
```

## Error Contract

Jobs additionally retain `error_fields`, defaulting to `{}` for older data.
Structured upstream `error.param` supplies field attribution; unknown errors
remain request-level messages. The WebUI only attaches a failed request's field
errors to a draft that still matches its submitted settings and edit inputs.

Response:

```json
{
  "detail": {
    "message": "Generation failed",
    "code": "generation_failed",
    "fields": {}
  }
}
```

Frontend should display `detail.message`. If the shape is unknown, display a
generic error.

Validation errors return `422` with `code: "invalid_request"` and field names in
`detail.fields`, for example `{"n": "...", "extra_body": "..."}`. Invalid uploads
and masks return `400`, missing image references return `404`, and upstream
request failures return `502` for synchronous operations. Background jobs retain
the same message/fields on their failed job record.
