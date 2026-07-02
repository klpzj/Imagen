# GPT Image API wrapper

[中文说明](README.zh-CN.md)

Small Python wrapper around the OpenAI Image API. It supports text-to-image
generation, image editing, local file output, and CLI usage.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:OPENAI_API_KEY="sk-your-api-key"
```

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

- `--model`: image model name, default from `OPENAI_IMAGE_MODEL` or `gpt-image-1`
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
that can occur on port `8000`.

Open:

```text
http://<frps-server>:15173
```

## WebUI design docs

- [Docs index](docs/README.md)
- [WebUI module design](docs/webui-module-design.md)
- [Backend modules](docs/backend-modules.md)
- [Frontend modules](docs/frontend-modules.md)
- [API and data contract](docs/api-and-data-contract.md)
- [Implementation plan](docs/implementation-plan.md)
- [Decision log](docs/decision-log.md)
- [Consistency audit](docs/consistency-audit.md)
- [Three-Codex work allocation](docs/three-codex-work-allocation.md)
- [V1 integration verification](docs/v1-integration-verification.md)
