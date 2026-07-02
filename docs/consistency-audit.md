# Documentation Consistency Audit

Date: 2026-07-02

## Result

The WebUI documents have been aligned around a smaller MVP:

- Text-to-image generation.
- Safe config loading.
- Generated image preview.
- Read-only history gallery.
- Manifest-backed metadata.
- Static serving for generated files.

The following features are now Post-MVP:

- Image editing.
- Mask upload.
- Canvas mask drawing.
- Delete image/history record.
- Single-image detail route.
- Job queue and cancellation.
- Production deployment.

## Issues Found

### Edit Was Both MVP And Deferred

Problem:

- `webui-module-design.md` said the first version should stay simple.
- `backend-modules.md`, `frontend-modules.md`, `api-and-data-contract.md`, and
  `implementation-plan.md` included edit routes and edit components in the
  first build path.

Resolution:

- Removed edit from MVP routes, components, state, API client, and acceptance
  criteria.
- Added edit to Post-MVP sections.

### Delete Was In History MVP Without A Stability Gate

Problem:

- History deletion was included before the manifest format had stabilized.
- This would add file deletion risk to the first version.

Resolution:

- Removed delete from MVP.
- Kept deletion as a Post-MVP route and store action.

### Route List And API Contract Did Not Match MVP Flow

Problem:

- The flow only required `/api/config`, `/api/generate`, and `/api/images`.
- The API contract also specified edit, detail, and delete endpoints.

Resolution:

- MVP API now includes:
  - `GET /api/health`
  - `GET /api/config`
  - `POST /api/generate`
  - `GET /api/images`
  - `/outputs/{filename}` static files
- Post-MVP API is listed separately.

### Frontend State Was Wider Than Needed

Problem:

- Store state included `mode`, `isEditing`, edit actions, and delete actions.
- Components included `EditPanel` and `UploadDropzone`.

Resolution:

- MVP frontend state is generation-only.
- Edit/upload components are documented as Post-MVP.

### Config Allowed Too Much Initial Fan-Out

Problem:

- `max_n` was set to 4 in the contract.
- First UI and backend should limit cost and latency risk.

Resolution:

- `max_n` is now 2 for MVP.

## Final MVP Contract

Backend:

```text
GET  /api/health
GET  /api/config
POST /api/generate
GET  /api/images
GET  /outputs/{filename}
```

Frontend:

```text
AppShell
GeneratePanel
ParameterControls
ImagePreview
HistoryGallery
ErrorToast
```

Data:

```text
outputs/
  manifest.json
  generated-image-files
```

Acceptance:

- Backend starts.
- Frontend starts.
- Config does not expose secrets.
- A real generation request succeeds through the WebUI.
- Generated image appears in preview.
- Generated image appears in history after refresh and after generation.

