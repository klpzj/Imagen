# Implementation Plan

This plan describes the current local WebUI target. The shipped surface includes
text generation, image editing, preview, download, history deletion, persisted
generation jobs, and managed local startup with optional FRP.

## Phase 1: Backend Foundation

Files:

- `backend/app.py`
- `backend/config.py`
- `backend/schemas.py`
- `backend/image_store.py`
- `backend/job_store.py`
- `backend/image_service.py`

Tasks:

1. Add FastAPI dependencies to `requirements.txt`.
2. Implement `GET /api/health`.
3. Implement safe config loading.
4. Implement `outputs/manifest.json` and `outputs/jobs.json` read/write helpers.
5. Implement `POST /api/generate`.
6. Implement `POST /api/edit`.
7. Implement job create/list/active/detail endpoints.
8. Implement history deletion.
9. Serve `outputs/` as static files.
10. Test one real generation request through the backend.

Acceptance:

- `GET /api/health` returns `{ "ok": true }`.
- `GET /api/config` does not expose secrets.
- `POST /api/generate` creates an image file and manifest record.
- `POST /api/jobs` persists queued/running/succeeded/failed task state.
- `DELETE /api/jobs/{job_id}` removes failed task records.
- `POST /api/edit` can create edited images from uploads or history images.
- `DELETE /api/images/{image_id}` removes the history record and local file.
- Generated image URL opens in the browser.

## Phase 2: Vue Shell

Files:

- `webui/package.json`
- `webui/vite.config.ts`
- `webui/src/main.ts`
- `webui/src/App.vue`
- `webui/src/styles/base.css`

Tasks:

1. Scaffold Vue 3 + Vite + TypeScript.
2. Add Pinia.
3. Add base layout with toolbar, resizable left/right/bottom regions, preview,
   and history region.
4. Add API client base wrapper.
5. Load config/history at startup.

Acceptance:

- `npm run dev` starts successfully.
- Browser shows the app shell at `http://localhost:5173`.
- Config loads from backend.

## Phase 3: Generate Flow

Files:

- `GeneratePanel.vue`
- `ParameterControls.vue`
- `ImagePreview.vue`
- `imageApi.ts`
- `imageStore.ts`

Tasks:

1. Build prompt and parameter controls.
2. Wire persisted job generation request.
3. Show loading state.
4. Show generated result in preview.
5. Add download, copy prompt, reuse prompt, and open actions.

Acceptance:

- User can generate from the WebUI.
- Latest result appears without page refresh.
- Refreshing during generation restores active/failed task state.
- Errors are visible and understandable.

## Phase 4: History Gallery

Files:

- `HistoryGallery.vue`
- `imageStore.ts`

Tasks:

1. Render thumbnails from `/api/images`.
2. Select historical image into preview.
3. Show compact metadata.
4. Refresh history after generation or edit.
5. Delete history records.
6. Download historical images.

Acceptance:

- Refreshing the browser keeps history.
- Clicking a thumbnail updates the preview.
- Newly generated images appear in history without page refresh.
- Failed tasks remain visible after refresh.
- Deleted images disappear from history and local output storage.

## Phase 5: Edit Flow

Files:

- `EditPanel.vue`
- `ModePanel.vue`
- `ParameterControls.vue`
- `ImagePreview.vue`
- `imageApi.ts`
- `imageStore.ts`

Tasks:

1. Add generate/edit mode switching.
2. Support uploaded PNG/JPEG/WebP source images.
3. Support reusing history images as edit sources.
4. Wire multipart edit request.
5. Show edited results in preview and history.

Acceptance:

- User can edit with uploaded source images.
- User can edit using a selected history image.
- Edited images are persisted with `type: "edit"` metadata.

## Phase 6: Lifecycle, Polish, And Verification

Tasks:

1. Responsive layout pass.
2. Loading and disabled button pass.
3. Empty state pass.
4. Error state pass.
5. Add `start-frp-webui.bat` and `stop-frp-webui.bat` lifecycle scripts.
6. Run backend syntax checks.
7. Run frontend build.
8. Test one real generation through UI.

Acceptance:

- UI works at desktop and mobile widths.
- No obvious text overflow.
- Frontend build succeeds.
- Backend starts cleanly.
- Real generation succeeds through WebUI.
- Managed startup does not leak backend, frontend, or frpc processes.

## Backlog

- Single-image detail route.
- Canvas mask drawing.
- Multi-job queue management and cancellation.
- Production deployment packaging.
- User accounts and permissions.

## Start Commands

Backend:

```powershell
python -m uvicorn backend.app:app --reload --port 18000
```

Frontend:

```powershell
cd webui
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

Managed local startup with optional FRP:

```powershell
.\start-frp-webui.bat
```

Managed stop:

```powershell
.\stop-frp-webui.bat
```
