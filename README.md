# Imagen (historical repository)

[中文说明](README.zh-CN.md)

Since 2026-10-14, daily use, development, tests and releases of Imagen are maintained in [PersonalStation](https://github.com/klpzj/PersonalStation). This repository preserves the old Vue/FastAPI application, direct Python client and design history.

Use the [production Imagen workshop](https://bunnykloud.site/index/workshop/imagen) and its [native parameter guide](https://github.com/klpzj/PersonalStation/blob/main/docs/imagen-parameters.md). The [consolidation record](https://github.com/klpzj/PersonalStation/blob/main/docs/architecture/imagen-consolidation-20261014.md) documents feature coverage, checked callers, runtime dependencies and archived data.

## Active implementation

PersonalStation owns the Svelte workbench, Rust API, jobs, image history, media publication, Node CLI and migration tool. Production credentials live outside either repository; data lives in `DATA_DIR/imagen`. The old FastAPI/Vue services and FRP tunnel are unnecessary for that deployment.

From the PersonalStation repository:

```sh
node scripts/imagen.mjs --help
node scripts/imagen.mjs generate --quality low -o ./outputs "A simple red apple on a white background"
node scripts/imagen.mjs edit --image ./input.png "Replace the background with a studio backdrop"
```

The CLI defaults to the local Rust API. Add `--api-url https://bunnykloud.site/index` to use the production station. Upstream credentials and connection settings belong to the Rust server.

## Preserved materials

- Complete historical [English](docs/legacy/README.md) and [Chinese](docs/legacy/README.zh-CN.md) guides, with commands run from this repository root.
- [Historical design and verification documents](docs/README.md).
- `gpt_image_client.py`, the direct Python module/CLI. The native Node CLI uses the station API and does not provide the same Python import interface. No external caller was found in the checked projects or skills.
- The original MIT `LICENSE` and Git history.

All eight legacy jobs are present in the station. A verified Git bundle, original metadata and one previously omitted nested image are preserved locally under PersonalStation's `data/archives/imagen-20261014`; the old credential file is backed up separately outside repositories. Browser drafts and presets have different storage keys and export formats, so they are not automatically migrated.

The source tree and GitHub repository remain available as history. New features and fixes belong in PersonalStation.
