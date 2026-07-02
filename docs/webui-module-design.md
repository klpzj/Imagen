# WebUI Module Design

This document describes the planned Vue WebUI for the GPT image generation
tool. The MVP should be a local single-user workstation app: open the browser,
enter a prompt, tune a small set of parameters, generate images, preview the
result, and browse generation history.

## Goals

- Keep API keys and base URLs on the Python backend.
- Reuse the existing `gpt_image_client.py` wrapper.
- Provide a modern image generation workspace instead of a landing page.
- Persist generated files and metadata under `outputs/`.
- Keep the first version simple enough to ship quickly, while leaving clear
  extension points.

## Non Goals

- No account system.
- No multi-user permission model.
- No remote deployment design in the first version.
- No image edit workflow in the MVP.
- No online mask painting in the MVP.
- No background queue or distributed worker system in the first version.
- No delete workflow in the MVP.

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
- Stores image files and `manifest.json`.
- Can be managed by future app actions after V1.
- Must not be committed to version control.

## First Version User Flow

1. User starts backend and frontend dev server.
2. Browser opens the Vue app.
3. App loads `/api/config` and `/api/images`.
4. User enters prompt and generation parameters.
5. App posts to `/api/generate`.
6. Backend calls `GPTImageClient.generate`.
7. Generated files are saved under `outputs/`.
8. Backend records metadata in `outputs/manifest.json`.
9. App displays the generated image and updates the history gallery.

## UI Layout

Desktop:

```text
+-----------------------------------------------------------+
| Top toolbar: app name, model, status                       |
+------------------+----------------------+-----------------+
| Left panel       | Main preview         | Right history   |
| Prompt           | Current image        | Thumbnails      |
| Parameters       | Download / reuse     | Metadata        |
| Generate         | Loading / errors     | Metadata        |
+------------------+----------------------+-----------------+
```

Mobile:

- Toolbar at top.
- Parameters stacked above preview.
- History becomes a horizontal strip below preview.

## Implementation Order

1. Add backend API and manifest storage.
2. Add minimal Vue shell with generate flow.
3. Add history gallery and selected image preview.
4. Polish loading, errors, empty states, and basic responsive layout.

## MVP Scope

Included:

- `GET /api/health`
- `GET /api/config`
- `POST /api/generate`
- `GET /api/images`
- Static serving for generated files under `/outputs/`
- Prompt input
- Size, quality, format, count, and background controls
- Latest result preview
- History gallery loaded from `outputs/manifest.json`
- Download generated image

Deferred:

- Image edit and mask upload
- Delete image/history record
- Dedicated single-image detail route
- Canvas mask drawing
- Queue management
- User accounts
- Production deployment
