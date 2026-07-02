# Implementation Plan

This plan breaks the slim MVP into small, testable steps. MVP means text image
generation, preview, and history. Edit and delete are intentionally deferred.

## Phase 1: Backend Foundation

Files:

- `backend/app.py`
- `backend/config.py`
- `backend/schemas.py`
- `backend/image_store.py`
- `backend/image_service.py`

Tasks:

1. Add FastAPI dependencies to `requirements.txt`.
2. Implement `GET /api/health`.
3. Implement safe config loading.
4. Implement `outputs/manifest.json` read/write helpers.
5. Implement `POST /api/generate`.
6. Serve `outputs/` as static files.
7. Test one real generation request through the backend.

Acceptance:

- `GET /api/health` returns `{ "ok": true }`.
- `GET /api/config` does not expose secrets.
- `POST /api/generate` creates an image file and manifest record.
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
3. Add base layout with toolbar, left panel, preview, and history region.
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
2. Wire generate request.
3. Show loading state.
4. Show generated result in preview.
5. Add download and copy prompt actions.

Acceptance:

- User can generate from the WebUI.
- Latest result appears without page refresh.
- Errors are visible and understandable.

## Phase 4: History Gallery

Files:

- `HistoryGallery.vue`
- `imageStore.ts`

Tasks:

1. Render thumbnails from `/api/images`.
2. Select historical image into preview.
3. Show compact metadata.
4. Refresh history after generation.

Acceptance:

- Refreshing the browser keeps history.
- Clicking a thumbnail updates the preview.
- Newly generated images appear in history without page refresh.

## Phase 5: MVP Polish And Verification

Tasks:

1. Responsive layout pass.
2. Loading and disabled button pass.
3. Empty state pass.
4. Error state pass.
5. Run backend syntax checks.
6. Run frontend build.
7. Test one real generation through UI.

Acceptance:

- UI works at desktop and mobile widths.
- No obvious text overflow.
- Frontend build succeeds.
- Backend starts cleanly.
- Real generation succeeds through WebUI.

## Post-MVP Backlog

- Image edit route and UI.
- Upload dropzone and optional mask upload.
- Delete history record and generated file.
- Single-image detail route.
- Canvas mask drawing.
- Job queue or cancellation.

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
