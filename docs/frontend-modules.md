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
- Own top-level layout.
- Render `AppShell`.
- Show global error toast when needed.

Startup flow:

```text
onMounted
  -> imageStore.loadConfig()
  -> imageStore.loadHistory()
```

## `components/AppShell.vue`

Responsibilities:

- Provide the three-column desktop layout.
- Provide responsive mobile layout.
- Place shared toolbar controls.

Main regions:

- Left: `GeneratePanel`.
- Center: `ImagePreview`.
- Right: `HistoryGallery`.

## `components/GeneratePanel.vue`

Responsibilities:

- Prompt input.
- Parameter controls.
- Generate button.
- Clear prompt action.
- Disable submit when prompt is empty or request is running.

State used:

- `prompt`
- `options`
- `imageStore.isGenerating`

Actions:

- `imageStore.generate(prompt, options)`

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
  - image count
  - background
- Receive allowed values from backend config.
- Emit a complete options object.

Control types:

- Select menus for model, size, quality, format.
- Stepper or numeric input for count.
- Segmented control for background.

## `components/ImagePreview.vue`

Responsibilities:

- Display selected or latest image.
- Show empty state when no image exists.
- Show loading state during generation.
- Show image metadata.
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

Desktop behavior:

- Vertical thumbnail list.
- Selected state visible.

Mobile behavior:

- Horizontal thumbnail strip.

## Post-MVP: `components/EditPanel.vue`

Responsibilities:

- Upload source image.
- Optional mask upload.
- Edit instruction input.
- Shared parameter controls.
- Submit edit request.

## Post-MVP: `components/UploadDropzone.vue`

Responsibilities:

- Handle drag and drop.
- Handle file picker.
- Preview selected image.
- Validate image MIME type.
- Emit selected `File`.

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
```

Post-MVP:

```ts
export function editImage(payload: EditPayload): Promise<ImageRecord[]>
export function deleteImage(id: string): Promise<void>
```

## `stores/imageStore.ts`

Use Pinia for shared app state.

State:

```ts
config: AppConfig | null
images: ImageRecord[]
selectedImageId: string | null
isGenerating: boolean
error: string | null
```

Getters:

```ts
selectedImage
latestImage
historyImages
isBusy
```

Actions:

```ts
loadConfig()
loadHistory()
generate(prompt, options)
selectImage(id)
clearError()
```

Post-MVP actions:

```ts
edit(payload)
deleteImage(id)
```

## `types/image.ts`

Shared frontend types:

```ts
export interface ImageOptions {
  model?: string
  size: string
  quality: string
  output_format: string
  background?: string | null
  n: number
}

export interface ImageRecord {
  id: string
  type: "generate"
  filename: string
  url: string
  prompt: string
  model: string
  size: string
  quality: string
  format: string
  created_at: string
}
```

Post-MVP should widen `type` to `"generate" | "edit"` when edit mode is added.

## Styling

Use a single `styles/base.css` file first. Introduce component-scoped CSS only
when a component has complex local layout.

Layout constraints:

- Stable preview aspect ratio.
- Fixed toolbar height.
- Scroll inside history panel, not the whole page.
- Buttons must not resize during loading state.
- Text must not overflow inside controls.
