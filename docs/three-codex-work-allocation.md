# Three-Codex Work Allocation

This document splits V1 WebUI construction across three Codex workers. V1 means
the slim MVP documented in `api-and-data-contract.md`: text generation,
preview, and read-only history.

## V1 Source Of Truth

Use these documents as the contract:

1. `docs/api-and-data-contract.md`
2. `docs/backend-modules.md`
3. `docs/frontend-modules.md`
4. `docs/implementation-plan.md`
5. `docs/consistency-audit.md`

If these documents conflict, resolve in this order:

1. `api-and-data-contract.md`
2. `consistency-audit.md`
3. backend/frontend module docs
4. implementation plan

Do not add Post-MVP features during V1 implementation.

## Workers

## Task Matrix

| Area | Owner | Inputs | Outputs |
| --- | --- | --- | --- |
| FastAPI routes | Codex A | API contract, existing image client | `backend/` service |
| Manifest storage | Codex A | `outputs/`, record schema | `outputs/manifest.json` |
| Vue workspace UI | Codex B | API contract, frontend module doc | `webui/` app |
| API client and store | Codex B | V1 route shapes | typed frontend calls |
| End-to-end verification | Codex C | backend + frontend outputs | integration report |
| Contract corrections | Codex C leads, A/B confirm | implementation mismatch | updated docs |

Only Codex C should coordinate cross-cutting doc updates after A and B begin
implementation.

### Codex A: Backend API

Mission:

- Implement the FastAPI backend for the V1 contract.

Primary files:

- `backend/app.py`
- `backend/config.py`
- `backend/schemas.py`
- `backend/image_service.py`
- `backend/image_store.py`
- `requirements.txt`

Allowed shared files:

- `gpt_image_client.py` only for small compatibility changes needed by backend.
- `docs/api-and-data-contract.md` only if a real contract issue is found.

Must not edit:

- `webui/` files.
- Frontend design documents unless documenting a backend contract correction.
- `auth.json`.

Deliverables:

- `GET /api/health`
- `GET /api/config`
- `POST /api/generate`
- `GET /api/images`
- Static serving for `/outputs/{filename}`
- Manifest persistence at `outputs/manifest.json`
- Backend startup command works:

```powershell
python -m uvicorn backend.app:app --reload --port 18000
```

Acceptance checks:

- Health returns `{ "ok": true }`.
- Config response excludes API key, base URL, and raw auth data.
- Generate route creates image files and manifest records.
- Image URLs returned by API can be opened through backend static serving.
- `python -m py_compile backend/app.py backend/config.py backend/schemas.py backend/image_service.py backend/image_store.py` passes.

### Codex B: Frontend UI

Mission:

- Implement the Vue 3 WebUI against the frozen V1 API contract.

Primary files:

- `webui/package.json`
- `webui/vite.config.ts`
- `webui/index.html`
- `webui/src/main.ts`
- `webui/src/App.vue`
- `webui/src/api/client.ts`
- `webui/src/api/imageApi.ts`
- `webui/src/components/AppShell.vue`
- `webui/src/components/GeneratePanel.vue`
- `webui/src/components/ParameterControls.vue`
- `webui/src/components/ImagePreview.vue`
- `webui/src/components/HistoryGallery.vue`
- `webui/src/components/ErrorToast.vue`
- `webui/src/stores/imageStore.ts`
- `webui/src/types/image.ts`
- `webui/src/styles/base.css`

Allowed shared files:

- None by default.
- If the API contract appears wrong, stop and report the required contract
  change instead of silently changing backend assumptions.

Must not edit:

- `backend/` files.
- `gpt_image_client.py`.
- `auth.json`.

Deliverables:

- Browser opens directly into the tool workspace.
- Prompt and parameter controls call `POST /api/generate`.
- Latest result appears in `ImagePreview`.
- History loads from `GET /api/images`.
- New results appear in history after generation.
- Download and copy prompt actions work.

Acceptance checks:

- `npm install` succeeds.
- `npm run build` succeeds.
- UI handles empty, loading, error, and success states.
- UI does not expose API key or upstream base URL.
- UI does not implement edit/delete in V1.

### Codex C: Integration And Verification

Mission:

- Keep both sides aligned, run end-to-end checks, and fix only integration
  issues that do not belong clearly to A or B.

Primary files:

- `docs/`
- `README.md`
- Optional small scripts under `scripts/` if useful for local checks.

Allowed shared files:

- Backend or frontend files only for narrow integration fixes after confirming
  the owner boundary.

Must not edit:

- `auth.json`.
- Large frontend redesigns.
- Backend feature scope beyond V1.

Deliverables:

- Verify backend and frontend can run together.
- Verify V1 route shapes match `api-and-data-contract.md`.
- Verify generated image can be created through WebUI.
- Update docs if implementation details change.
- Produce a final integration note with commands run and results.

Acceptance checks:

- Backend starts on `http://localhost:18000`.
- Frontend starts on `http://localhost:5173`.
- Real generation succeeds through WebUI using the configured base URL.
- `outputs/manifest.json` contains the generated record.
- Refreshing WebUI reloads history.

## Interface Alignment Surface

This surface is frozen for V1. Any worker needing a change must update
`docs/api-and-data-contract.md` first and notify the other workers.

### `GET /api/health`

Response:

```json
{
  "ok": true
}
```

### `GET /api/config`

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

Forbidden response fields:

- API key.
- upstream base URL.
- raw auth config.

### `POST /api/generate`

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
      "created_at": "2026-07-02T23:30:15+08:00",
      "revised_prompt": null
    }
  ]
}
```

### `GET /api/images`

Response:

```json
{
  "images": []
}
```

When records exist, `images` uses the same `ImageRecord` shape returned by
`POST /api/generate`. Records are newest first.

### Error Shape

```json
{
  "detail": {
    "message": "Generation failed",
    "code": "generation_failed"
  }
}
```

Frontend displays `detail.message`. Backend should use stable `code` values.

## Merge Order

1. Codex A lands backend foundation.
2. Codex B lands frontend shell and generate flow using mocked or empty backend
   responses if needed.
3. Codex A and B align on real API calls.
4. Codex C runs integration checks and fixes narrow mismatches.
5. Codex C updates docs and final verification notes.

## Conflict Rules

- Contract conflicts are resolved in `docs/api-and-data-contract.md`.
- File ownership conflicts are resolved by the worker listed as owner above.
- Do not widen scope to edit/delete to solve V1 issues.
- Do not expose secrets to the browser.
- Do not replace `gpt_image_client.py` wholesale; adapt it narrowly.
- Do not delete generated files in V1.

## Shared Done Definition

V1 is done when:

- Backend and frontend start with the documented commands.
- A real generation request succeeds through the WebUI.
- The generated image previews in the center panel.
- The generated image appears in history after generation.
- Refreshing the browser reloads the history from backend.
- API key and upstream base URL are not exposed in frontend responses.
- Post-MVP features remain unimplemented.

## Codex Prompts

### Prompt For Codex A: Backend API

```text
You are Codex A working in C:\Users\klpzj\Downloads\study\imagen.

Implement only the V1 FastAPI backend for the GPT image WebUI. Read these files
first:

- docs/api-and-data-contract.md
- docs/backend-modules.md
- docs/implementation-plan.md
- docs/consistency-audit.md
- gpt_image_client.py

Scope:

- Add backend/app.py, backend/config.py, backend/schemas.py,
  backend/image_service.py, backend/image_store.py.
- Update requirements.txt with backend dependencies.
- Implement only GET /api/health, GET /api/config, POST /api/generate,
  GET /api/images, and static /outputs serving.
- Persist records to outputs/manifest.json.
- Reuse GPTImageClient and auth.json. Never print or expose API_KEY.

Do not implement edit, mask upload, delete, single-image detail, auth UI, queue,
or production deployment.

Before finishing, run:

- python -m py_compile backend/app.py backend/config.py backend/schemas.py backend/image_service.py backend/image_store.py
- python -m uvicorn backend.app:app --port 18000 if practical

Final response must include changed files, how to start the backend, and test
results.
```

### Prompt For Codex B: Frontend UI

```text
You are Codex B working in C:\Users\klpzj\Downloads\study\imagen.

Implement only the V1 Vue 3 + Vite + TypeScript WebUI. Read these files first:

- docs/api-and-data-contract.md
- docs/frontend-modules.md
- docs/webui-module-design.md
- docs/implementation-plan.md
- docs/consistency-audit.md

Scope:

- Create webui/ with Vue 3, Vite, TypeScript, and Pinia.
- Implement AppShell, GeneratePanel, ParameterControls, ImagePreview,
  HistoryGallery, ErrorToast, API client, image store, shared types, and base
  CSS.
- Call GET /api/config, GET /api/images, and POST /api/generate.
- Use relative `/api` and `/outputs` paths by default. Vite proxies them to
  `http://localhost:18000`.
- Make the first screen the actual tool workspace.

Do not implement edit, upload, mask drawing, delete, auth entry, queue, or
landing page.

Before finishing, run:

- npm install
- npm run build

Final response must include changed files, how to start the frontend, and build
results.
```

### Prompt For Codex C: Integration And Verification

```text
You are Codex C working in C:\Users\klpzj\Downloads\study\imagen.

Your job is V1 integration and verification, not new feature development. Read
these files first:

- docs/three-codex-work-allocation.md
- docs/api-and-data-contract.md
- docs/implementation-plan.md
- docs/consistency-audit.md

Scope:

- Start or verify backend on http://localhost:18000.
- Start or verify frontend on http://localhost:5173.
- Confirm GET /api/config does not expose API key, base URL, or raw auth.json.
- Confirm POST /api/generate works through the backend.
- Confirm the WebUI can generate one real image.
- Confirm outputs/manifest.json records the image.
- Confirm refreshing WebUI reloads history.
- Fix only narrow integration mismatches. If a larger issue belongs to backend
  or frontend ownership, document it and hand it back.
- Update docs if final commands or implementation details changed.

Do not implement Post-MVP features.

Final response must include commands run, pass/fail results, generated image
path if any, and unresolved issues.
```
