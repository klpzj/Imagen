# Decision Log

## Keep Credentials On The Backend

Decision:

- The browser will never receive `API_KEY`, `OPENAI_API_KEY`, or raw `auth.json`.

Reason:

- Frontend code is visible to the browser. Putting credentials there would leak
  access to the upstream image API.

## Use FastAPI For Backend

Decision:

- Use FastAPI instead of adding image generation directly to Vite.

Reason:

- The existing client is Python.
- Future multipart upload support is straightforward when edit mode is added.
- Static serving for generated files is simple.

## Use Manifest File Instead Of Database

Decision:

- Store history in `outputs/manifest.json` for the first version.

Reason:

- Single-user local tool.
- Easy to inspect and reset.
- Avoids adding database setup before it is needed.

Future trigger for database:

- Multiple users.
- Large history.
- Search/filter beyond simple metadata.
- Concurrent long-running jobs.

## Defer Image Editing From MVP

Decision:

- The MVP will not include image editing, mask upload, or canvas mask drawing.

Reason:

- Text-to-image generation proves the full backend, base URL, file output,
  manifest, and UI preview pipeline.
- Editing adds multipart uploads, temporary files, wider record types, and more
  UI states.
- Removing edit from MVP reduces risk without blocking later expansion.

Future extension:

- Add upload-based edit first.
- Add brush controls, undo/redo, and generated alpha mask export later.

## Defer Deletion From MVP

Decision:

- MVP history is read-only from the UI.

Reason:

- Avoid accidental file loss while the manifest format is still changing.
- Deletion can be added after the history record shape is stable.

## No Canvas Mask Editor In First Version

Decision:

- The first edit version should support mask file upload before canvas mask
  drawing.

Reason:

- Canvas mask drawing adds substantial UI complexity.
- Uploading a mask is enough to validate the edit pipeline.

Future extension:

- Add brush controls, undo/redo, and generated alpha mask export.

## Direct Tool Workspace UI

Decision:

- The first screen is the generation workspace.

Reason:

- This is a local productivity tool. A landing page would slow down the primary
  workflow.
