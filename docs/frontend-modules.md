# Frontend Modules

The frontend should be a Vue 3 + Vite + TypeScript single-page app. It should
open directly into the image generation workspace.

## Design Direction

- Quiet, dense, work-focused tool UI.
- No marketing landing page.
- No decorative card nesting.
- Clear controls and predictable layout.
- Main image preview should be the visual focus.
- History should be easy to scan.

## `src/App.vue`

Responsibilities:

- Load initial config and history.
- Restore active or recent generation jobs.
- Own top-level layout.
- Render `AppShell`.
- Show global error toast when needed.

Startup flow:

```text
onMounted
  -> imageStore.loadConfig()
  -> imageStore.loadHistory()
  -> imageStore.restoreJobs()
```

## `components/AppShell.vue`

Responsibilities:

- Provide the three-column desktop layout.
- Provide resizable left, right, and bottom regions.
- Provide responsive mobile layout.
- Place shared toolbar controls.

Main regions:

- Left: `ModePanel`, `GeneratePanel`, and `EditPanel`.
- Center: `ImagePreview`.
- Right: `HistoryGallery`.
- Bottom: compact job/status strip when needed.

## `components/GeneratePanel.vue`

Responsibilities:

- Prompt input.
- Parameter controls.
- Generate button.
- Clear prompt action.
- Disable submit when prompt is empty or request is running.
- Submit generation as a persisted job so refreshes keep task state.

State used:

- `prompt`
- `options`
- `imageStore.isGenerating`

Actions:

- `imageStore.createGenerationJob(prompt, options)`

Validation:

- Trim prompt before submit.
- Reject empty prompt.
- Clamp `n` to backend-supported range.

## `components/ParameterControls.vue`

Responsibilities:

- Render reusable controls for:
  - model
  - size
  - quality
  - output format
  - moderation
  - image count
- Receive allowed values from backend config.
- Emit a complete options object.

Control types:

- Select menus for model, size, quality, format, and moderation.
- Stepper or numeric input for count.

## `components/ImagePreview.vue`

Responsibilities:

- Display selected or latest image.
- Show empty state when no image exists.
- Show loading state during generation.
- Show image metadata.
- Support dynamic preview sizing and fullscreen preview.
- Provide actions:
  - download
  - copy prompt
  - reuse prompt
  - open image in browser tab

Data displayed:

- image URL
- prompt
- model
- size
- quality
- format
- created time

## `components/HistoryGallery.vue`

Responsibilities:

- Render historical images from the backend.
- Click thumbnail to select.
- Show compact metadata.
- Delete history records.
- Download image files through the API helper.

Desktop behavior:

- Vertical thumbnail list.
- Selected state visible.

Mobile behavior:

- Horizontal thumbnail strip.

## `components/ModePanel.vue`

Responsibilities:

- Switch between generate and edit workflows.
- Keep mode switching compact and visible in the left panel.

## `components/EditPanel.vue`

Responsibilities:

- Upload source image.
- Reuse existing history images as edit sources.
- Edit instruction input.
- Shared parameter controls.
- Submit edit request.

Allowed MIME types:

- `image/png`
- `image/jpeg`
- `image/webp`

## `components/ErrorToast.vue`

Responsibilities:

- Display API and validation errors.
- Provide dismiss action.
- Auto-hide non-critical errors after a short delay.

## `api/client.ts`

Responsibilities:

- Create a small fetch wrapper.
- Prefix all calls with backend base URL.
- Parse JSON errors.
- Throw typed errors for the store.

Development backend URL:

```ts
const API_BASE = import.meta.env.VITE_API_BASE ?? "";
```

When `API_BASE` is empty, frontend calls use relative `/api` and `/outputs`
paths. The Vite dev server proxies them to `http://localhost:18000`.

## `api/imageApi.ts`

Responsibilities:

```ts
export function getConfig(): Promise<AppConfig>
export function listImages(): Promise<ImageRecord[]>
export function generateImage(payload: GeneratePayload): Promise<ImageRecord[]>
export function editImage(payload: EditPayload): Promise<ImageRecord[]>
export function createGenerationJob(payload: GeneratePayload): Promise<GenerationJob>
export function getGenerationJob(id: string): Promise<GenerationJob>
export function getActiveGenerationJob(): Promise<GenerationJob | null>
export function listGenerationJobs(): Promise<GenerationJob[]>
export function deleteGenerationJob(id: string): Promise<GenerationJob[]>
export function deleteImage(id: string): Promise<ImageRecord[]>
```

## `stores/imageStore.ts`

Use Pinia for shared app state.

State:

```ts
config: AppConfig | null
images: ImageRecord[]
selectedImageId: string | null
jobs: GenerationJob[]
activeJobId: string | null
error: string | null
```

Getters:

```ts
selectedImage
latestImage
historyImages
isBusy
activeJob
```

Actions:

```ts
loadConfig()
loadHistory()
createGenerationJob(prompt, options)
restoreJobs()
pollJob(id)
edit(payload)
deleteImage(id)
selectImage(id)
clearError()
```

## `types/image.ts`

Shared frontend types:

```ts
export interface ImageOptions {
  model?: string
  size: string
  quality: string
  output_format: string
  moderation: string
  n: number
}

export interface ImageRecord {
  id: string
  type: "generate" | "edit"
  filename: string
  url: string
  prompt: string
  model: string
  size: string
  quality: string
  format: string
  moderation?: string | null
  created_at: string
}
```

## Styling

Use a single `styles/base.css` file first. Introduce component-scoped CSS only
when a component has complex local layout.

Layout constraints:

- Stable preview aspect ratio.
- Fixed toolbar height.
- Scroll inside history panel, not the whole page.
- Buttons must not resize during loading state.
- Text must not overflow inside controls.
