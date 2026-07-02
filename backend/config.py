from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gpt_image_client import DEFAULT_BASE_URL, DEFAULT_MODEL


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUTH_PATH = PROJECT_ROOT / "auth.json"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
MANIFEST_PATH = OUTPUTS_DIR / "manifest.json"

MODELS = ("gpt-image-1",)
SIZES = ("1024x1024", "1024x1536", "1536x1024")
QUALITIES = ("auto", "low", "medium", "high")
OUTPUT_FORMATS = ("png", "jpeg", "webp")
BACKGROUNDS = ("auto", "transparent", "opaque")
MAX_N = 2


@dataclass(frozen=True)
class BackendSettings:
    api_key: str | None
    base_url: str
    default_model: str
    auth_path: Path
    outputs_dir: Path
    manifest_path: Path


def load_auth_config(path: Path = AUTH_PATH) -> dict[str, str]:
    if not path.is_file():
        return {}

    with path.open("r", encoding="utf-8") as handle:
        data: Any = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"Auth file must contain a JSON object: {path}")

    return {str(key): str(value) for key, value in data.items() if value is not None}


def get_backend_settings() -> BackendSettings:
    auth_config = load_auth_config()
    api_key = (
        auth_config.get("API_KEY")
        or auth_config.get("OPENAI_API_KEY")
        or auth_config.get("api_key")
        or os.getenv("OPENAI_API_KEY")
    )
    base_url = (
        auth_config.get("OPENAI_BASE_URL")
        or auth_config.get("BASE_URL")
        or auth_config.get("base_url")
        or os.getenv("OPENAI_BASE_URL")
        or DEFAULT_BASE_URL
    )
    default_model = (
        auth_config.get("OPENAI_IMAGE_MODEL")
        or auth_config.get("IMAGE_MODEL")
        or os.getenv("OPENAI_IMAGE_MODEL")
        or DEFAULT_MODEL
    )

    return BackendSettings(
        api_key=api_key,
        base_url=base_url,
        default_model=default_model,
        auth_path=AUTH_PATH,
        outputs_dir=OUTPUTS_DIR,
        manifest_path=MANIFEST_PATH,
    )


def get_safe_config() -> dict[str, object]:
    settings = get_backend_settings()
    default_model = settings.default_model if settings.default_model in MODELS else DEFAULT_MODEL
    return {
        "default_model": default_model,
        "models": list(MODELS),
        "sizes": list(SIZES),
        "qualities": list(QUALITIES),
        "formats": list(OUTPUT_FORMATS),
        "backgrounds": list(BACKGROUNDS),
        "max_n": MAX_N,
    }
