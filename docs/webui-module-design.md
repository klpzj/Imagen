# WebUI Module Design

This document describes the planned Vue WebUI for the GPT image generation
tool. The current target is a local single-user workstation app: open the
browser, enter a prompt or edit instruction, tune a small set of parameters,
generate images, preview the result, and browse generation history.

## Goals

- Keep API keys and base URLs on the Python backend.
- Reuse the existing `gpt_image_client.py` wrapper.
- Provide a modern image generation workspace instead of a landing page.
- Persist generated files and metadata under `outputs/`.
- Keep the implementation simple enough to run locally, while preserving task
  state across refreshes.

## Non Goals

- No account system.
- No multi-user permission model.
- No remote deployment design in the first version.
- No online mask painting in the MVP.
- No background queue or distributed worker system in the first version.

## Target Architecture

```text
Browser
  |
  | HTTP JSON
  v
FastAPI backend
  |
  | Python method calls
  v
gpt_image_client.py
  |
  | OpenAI-compatible Image API
  v
Configured base URL
```

## Directory Plan

```text
imagen/
  gpt_image_client.py
  auth.json
  backend/
    app.py
    config.py
    image_service.py
    image_store.py
    job_store.py
    schemas.py
  webui/
    index.html
    package.json
    vite.config.ts
    src/
      main.ts
      App.vue
      api/
        client.ts
        imageApi.ts
      components/
        AppShell.vue
        GeneratePanel.vue
        EditPanel.vue
        ModePanel.vue
        ParameterControls.vue
        ImagePreview.vue
        HistoryGallery.vue
        ErrorToast.vue
      stores/
        imageStore.ts
      types/
        image.ts
      styles/
        base.css
  outputs/
    manifest.json
    jobs.json
```

## Module Boundaries

`gpt_image_client.py`
- Owns OpenAI-compatible image API calls.
- Owns local file writing for generated image bytes.
- Reads credentials from explicit arguments, `auth.json`, or environment.
- Does not own HTTP routes, browser concerns, or history browsing behavior.

`backend/`
- Owns HTTP API, validation, metadata, and static file serving.
- Calls `gpt_image_client.py`.
- Returns safe config to the browser.
- Never returns the API key.

`webui/`
- Owns prompt entry, generation parameters, preview, history gallery, and
  downloads.
- Talks only to local backend routes.
- Does not know the API key or upstream base URL.

`outputs/`
- Stores image files, `manifest.json`, and `jobs.json`.
- Can be managed by local app actions.
- Must not be committed to version control.

## First Version User Flow

1. User starts backend and frontend dev server.
2. Browser opens the Vue app.
3. App loads `/api/config` and `/api/images`.
4. User enters prompt and generation parameters.
5. App posts to `/api/jobs` for persisted generation.
6. Backend runs `GPTImageClient.generate` in a background task.
7. Generated files are saved under `outputs/`.
8. Backend records metadata in `outputs/manifest.json`.
9. Backend records task state in `outputs/jobs.json`, including failures.
10. App displays the generated image and updates the history gallery.

## UI Layout

Desktop:

```text
+-----------------------------------------------------------+
| Top toolbar: app name, model, status                       |
+------------------+----------------------+-----------------+
| Left panel       | Main preview         | Right history   |
| Mode + prompt    | Current image        | Thumbnails      |
| Parameters       | Download / reuse     | Metadata        |
| Generate         | Loading / errors     | Metadata        |
+------------------+----------------------+-----------------+
```

Mobile:

- Toolbar at top.
- Parameters stacked above preview.
- History becomes a horizontal strip below preview.

## Implementation Order

1. Add backend API, manifest storage, and job storage.
2. Add Vue shell with generate and edit modes.
3. Add history gallery, selected image preview, download, and delete.
4. Polish loading, failures, empty states, resizable panels, and responsive layout.

## MVP Scope

Included:

- `GET /api/health`
- `GET /api/config`
- `POST /api/generate`
- `POST /api/edit`
- `POST /api/jobs`
- `GET /api/jobs`
- `GET /api/jobs/active`
- `GET /api/jobs/{job_id}`
- `DELETE /api/jobs/{job_id}`
- `GET /api/images`
- `DELETE /api/images/{image_id}`
- Static serving for generated files under `/outputs/`
- Prompt input
- Generate/edit mode switching
- Size, quality, format, count, and moderation controls
- Latest result preview
- History gallery loaded from `outputs/manifest.json`
- Job state loaded from `outputs/jobs.json`
- Download generated image
- Delete history records

Deferred:

- Dedicated single-image detail route
- Canvas mask drawing
- Multi-job queue management beyond one active local task
- User accounts
- Production deployment
