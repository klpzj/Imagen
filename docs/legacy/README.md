> Historical standalone guide, preserved on 2026-10-14. Active development is in PersonalStation. Run the commands below from the old Imagen repository root only when reproducing that version.

# GPT Image API wrapper

[中文说明](README.zh-CN.md)

This repository contains the standalone Vue/FastAPI version of Imagen and its
Python CLI. The [production Imagen workshop](https://bunnykloud.site/index/workshop/imagen)
uses the native Svelte/Rust implementation in
[PersonalStation](https://github.com/klpzj/PersonalStation). See its
[parameter guide](https://github.com/klpzj/PersonalStation/blob/main/docs/imagen-parameters.md)
for the deployed version; the feature notes below describe this standalone app.

Small Python wrapper and local WebUI around the OpenAI Image API. It supports
text-to-image generation, image editing, local file output, persisted task
state, history deletion, and CLI usage.

All parameter dropdowns accept direct text entry. The WebUI also supports
background, compression, input fidelity, PNG masks, style, response format,
timeout, extension JSON, independent drafts, named presets, and full settings
reuse. See the [upgrade notes](../parameter-editing-upgrade.zh-CN.md).

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:OPENAI_API_KEY="sk-your-api-key"
```

Requires OpenAI SDK 2.0.0+ and Pillow 10+.

You can also put credentials in `auth.json`:

```json
{
  "API_KEY": "sk-your-api-key"
}
```

## Generate

```powershell
python .\gpt_image_client.py generate "A clean product render of a white ceramic mug on a walnut desk"
```

## Edit

```powershell
python .\gpt_image_client.py edit --image .\input.png "Replace the background with a bright studio backdrop"
```

## Use as a module

```python
from gpt_image_client import GPTImageClient

client = GPTImageClient()
results = client.generate(
    "A minimal app icon for an image generation tool",
    size="1024x1024",
    quality="auto",
)

print(results[0].path)
```

Common options:

- `--model`: image model name, default from `OPENAI_IMAGE_MODEL` or `gpt-image-2`
- `--size`: image size, for example `1024x1024`
- `--quality`: `auto`, `low`, `medium`, or `high`
- `--format`: `png`, `jpeg`, or `webp`
- `--n`: number of images
- `-o/--out-dir`: output directory

## WebUI

Install backend dependencies:

```powershell
pip install -r requirements.txt
```

Start the backend:

```powershell
python -m uvicorn backend.app:app --reload --port 18000
```

Start the frontend:

```powershell
cd webui
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

Or start the backend, frontend, and optional frpc tunnel in one managed command
window:

```powershell
.\start-frp-webui.bat
```

Stop the managed processes:

```powershell
.\stop-frp-webui.bat
```

## FRP tunnel

The WebUI is configured to call `/api` and `/outputs` through the Vite dev
server, so frpc only needs to expose the frontend port.

Copy the example config and fill in your frps server address and token:

```powershell
Copy-Item .\frpc.example.toml .\frpc.toml
```

Start the backend in terminal 1:

```powershell
python -m uvicorn backend.app:app --reload --port 18000
```

Start the frontend in terminal 2:

```powershell
cd webui
npm run dev
```

Start frpc in terminal 3:

```powershell
.\frpc.exe -c .\frpc.toml
```

Or start backend, frontend, and frpc together in one command window:

```powershell
.\start-frp-webui.bat
```

The script uses backend port `18000` to avoid Windows socket permission issues
that can occur on port `8000`. It writes process metadata and logs under
`.run/`, prechecks ports `18000` and `5173`, and keeps the backend, frontend,
and frpc in one lifecycle group.

Stop the managed backend, frontend, and frpc processes:

```powershell
.\stop-frp-webui.bat
```

Open:

```text
http://<frps-server>:15173
```

## WebUI design docs

- [Docs index](../README.md)
- [WebUI module design](../webui-module-design.md)
- [Backend modules](../backend-modules.md)
- [Frontend modules](../frontend-modules.md)
- [API and data contract](../api-and-data-contract.md)
- [Implementation plan](../implementation-plan.md)
- [Decision log](../decision-log.md)
- [Consistency audit](../consistency-audit.md)
- [Three-Codex work allocation](../three-codex-work-allocation.md)
- [V1 integration verification](../v1-integration-verification.md)
