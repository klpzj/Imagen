# Documentation Consistency Audit

Date: 2026-07-03

## Result

The WebUI documents now describe the current local tool surface:

- Text-to-image generation with default model `gpt-image-2`.
- Image editing from uploads or existing history images.
- Safe config loading without exposing API keys or upstream base URLs.
- Generated image preview, fullscreen preview, download, copy, reuse, and open
  actions.
- History gallery with deletion.
- Manifest-backed image metadata in `outputs/manifest.json`.
- Persisted generation job state in `outputs/jobs.json`, including failed
  tasks.
- Managed Windows lifecycle scripts for backend, frontend, and optional FRP.

## Current API Contract

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
GET    /outputs/{filename}
```

## Alignment Notes

- The Vue WebUI no longer renders background controls.
- The backend still returns `backgrounds` in safe config and accepts
  `background` in `ImageOptions` for compatibility.
- Moderation uses `none` as an app-level sentinel. When selected, the backend
  omits the upstream moderation parameter instead of sending a non-official
  value.
- Historical planning documents such as `three-codex-work-allocation.md` and
  `v1-integration-verification.md` may still contain the earlier V1 scope and
  verification model because they record the state at that phase.

## Backlog Boundary

The following remain outside the current implementation:

- Canvas mask painting.
- Dedicated single-image detail route.
- Multi-job queue management and cancellation.
- User accounts and permissions.
- Production deployment packaging.

## Verification Checklist

- Backend syntax checks pass.
- Frontend production build passes.
- `git diff --check` passes.
- Runtime files, generated outputs, FRP binaries/config, and `auth.json` remain
  ignored.
