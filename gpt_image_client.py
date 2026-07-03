from __future__ import annotations

import argparse
import base64
import json
import os
import re
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_MODEL = "gpt-image-2"
DEFAULT_SIZE = "1024x1024"
DEFAULT_QUALITY = "auto"
DEFAULT_OUTPUT_FORMAT = "png"
DEFAULT_BASE_URL = "http://149.248.37.38:8080/"


@dataclass(frozen=True)
class ImageResult:
    """Local metadata for one generated or edited image."""

    path: Path
    index: int
    revised_prompt: str | None = None


class GPTImageClient:
    """Small OpenAI Image API wrapper for generation and editing."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        auth_file: str | Path | None = "auth.json",
        model: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "Missing dependency: install it with `pip install -r requirements.txt`."
            ) from exc

        auth_config = self._load_auth_config(auth_file)
        key = (
            api_key
            or auth_config.get("API_KEY")
            or auth_config.get("OPENAI_API_KEY")
            or auth_config.get("api_key")
            or os.getenv("OPENAI_API_KEY")
        )
        if not key:
            raise ValueError("API key is required. Set --api-key, auth.json, or OPENAI_API_KEY.")

        self.model = (
            model
            or auth_config.get("OPENAI_IMAGE_MODEL")
            or auth_config.get("IMAGE_MODEL")
            or os.getenv("OPENAI_IMAGE_MODEL")
            or DEFAULT_MODEL
        )
        self.base_url = (
            base_url
            or auth_config.get("OPENAI_BASE_URL")
            or auth_config.get("BASE_URL")
            or auth_config.get("base_url")
            or os.getenv("OPENAI_BASE_URL")
            or DEFAULT_BASE_URL
        )
        self.client = OpenAI(
            api_key=key,
            base_url=self.base_url,
            timeout=timeout,
        )

    @staticmethod
    def _load_auth_config(auth_file: str | Path | None) -> dict[str, str]:
        if not auth_file:
            return {}

        path = Path(auth_file)
        if not path.is_file():
            return {}

        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        if not isinstance(data, dict):
            raise ValueError(f"Auth file must contain a JSON object: {path}")

        return {str(key): str(value) for key, value in data.items() if value is not None}

    def generate(
        self,
        prompt: str,
        *,
        out_dir: str | Path = "outputs",
        filename_prefix: str | None = None,
        n: int = 1,
        size: str = DEFAULT_SIZE,
        quality: str = DEFAULT_QUALITY,
        output_format: str = DEFAULT_OUTPUT_FORMAT,
        background: str | None = None,
        moderation: str | None = "none",
    ) -> list[ImageResult]:
        """Generate one or more images from text and save them locally."""

        self._validate_prompt(prompt)
        params = {
            "model": self.model,
            "prompt": prompt,
            "n": n,
            "size": size,
            "quality": quality,
        }
        if background:
            params["background"] = background
        if moderation and moderation != "none":
            params["moderation"] = moderation
        if output_format:
            params["output_format"] = output_format

        response = self.client.images.generate(**params)
        return self._save_response_images(
            response,
            out_dir=out_dir,
            filename_prefix=filename_prefix or _slugify(prompt),
            output_format=output_format,
        )

    def edit(
        self,
        prompt: str,
        *,
        images: Iterable[str | Path],
        mask: str | Path | None = None,
        out_dir: str | Path = "outputs",
        filename_prefix: str | None = None,
        n: int = 1,
        size: str = DEFAULT_SIZE,
        quality: str = DEFAULT_QUALITY,
        output_format: str = DEFAULT_OUTPUT_FORMAT,
    ) -> list[ImageResult]:
        """Edit one or more input images from a text instruction."""

        self._validate_prompt(prompt)
        image_paths = [Path(path) for path in images]
        if not image_paths:
            raise ValueError("At least one image path is required for editing.")
        for path in image_paths:
            if not path.is_file():
                raise FileNotFoundError(path)

        mask_path = Path(mask) if mask else None
        if mask_path and not mask_path.is_file():
            raise FileNotFoundError(mask_path)

        opened_images = [path.open("rb") for path in image_paths]
        opened_mask = mask_path.open("rb") if mask_path else None
        try:
            params = {
                "model": self.model,
                "image": opened_images[0] if len(opened_images) == 1 else opened_images,
                "prompt": prompt,
                "n": n,
                "size": size,
                "quality": quality,
            }
            if opened_mask:
                params["mask"] = opened_mask
            if output_format:
                params["output_format"] = output_format

            response = self.client.images.edit(**params)
        finally:
            for handle in opened_images:
                handle.close()
            if opened_mask:
                opened_mask.close()

        return self._save_response_images(
            response,
            out_dir=out_dir,
            filename_prefix=filename_prefix or f"edit-{_slugify(prompt)}",
            output_format=output_format,
        )

    @staticmethod
    def _validate_prompt(prompt: str) -> None:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

    @staticmethod
    def _save_response_images(
        response: object,
        *,
        out_dir: str | Path,
        filename_prefix: str,
        output_format: str,
    ) -> list[ImageResult]:
        target_dir = Path(out_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        data = getattr(response, "data", None)
        if not data:
            raise RuntimeError("Image API returned no image data.")

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        extension = _normalize_extension(output_format)
        results: list[ImageResult] = []

        for index, item in enumerate(data, start=1):
            path = target_dir / f"{filename_prefix}-{timestamp}-{index}.{extension}"
            b64_json = getattr(item, "b64_json", None)
            url = getattr(item, "url", None)

            if b64_json:
                path.write_bytes(base64.b64decode(b64_json))
            elif url:
                with urllib.request.urlopen(url, timeout=60) as response_stream:
                    path.write_bytes(response_stream.read())
            else:
                raise RuntimeError("Image item did not include b64_json or url.")

            results.append(
                ImageResult(
                    path=path,
                    index=index,
                    revised_prompt=getattr(item, "revised_prompt", None),
                )
            )

        return results


def _slugify(value: str, *, max_length: int = 48) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return (slug or "image")[:max_length].strip("-") or "image"


def _normalize_extension(output_format: str) -> str:
    value = (output_format or DEFAULT_OUTPUT_FORMAT).lower().lstrip(".")
    if value == "jpeg":
        return "jpg"
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate or edit images with the OpenAI GPT Image API."
    )
    parser.add_argument("--api-key", default=None, help="Defaults to OPENAI_API_KEY.")
    parser.add_argument(
        "--auth-file",
        default="auth.json",
        help="JSON auth file. Supports API_KEY, OPENAI_API_KEY, and api_key.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Image model name.",
    )
    parser.add_argument("--base-url", default=None, help="Optional OpenAI-compatible base URL.")
    parser.add_argument("--timeout", type=float, default=None, help="Client timeout seconds.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser("generate", help="Create images from text.")
    _add_common_image_args(generate_parser, include_background=True)
    generate_parser.add_argument("prompt", nargs="+", help="Prompt text.")

    edit_parser = subparsers.add_parser("edit", help="Edit images from text.")
    _add_common_image_args(edit_parser)
    edit_parser.add_argument("--image", action="append", required=True, help="Input image path.")
    edit_parser.add_argument("--mask", default=None, help="Optional mask image path.")
    edit_parser.add_argument("prompt", nargs="+", help="Edit instruction.")

    return parser


def _add_common_image_args(
    parser: argparse.ArgumentParser, *, include_background: bool = False
) -> None:
    parser.add_argument("-o", "--out-dir", default="outputs", help="Output directory.")
    parser.add_argument("--prefix", default=None, help="Output filename prefix.")
    parser.add_argument("--n", type=int, default=1, help="Number of images.")
    parser.add_argument("--size", default=DEFAULT_SIZE, help="Image size, e.g. 1024x1024.")
    parser.add_argument("--quality", default=DEFAULT_QUALITY, help="Image quality.")
    parser.add_argument(
        "--format",
        dest="output_format",
        default=DEFAULT_OUTPUT_FORMAT,
        help="Output format, e.g. png, jpeg, or webp.",
    )
    if include_background:
        parser.add_argument(
            "--background",
            default=None,
            help="Generation background, e.g. auto, transparent, or opaque.",
        )
        parser.add_argument(
            "--moderation",
            default="none",
            help="Image moderation strictness, e.g. none, auto, or low.",
        )


def main() -> int:
    args = build_parser().parse_args()
    client = GPTImageClient(
        api_key=args.api_key,
        auth_file=args.auth_file,
        model=args.model,
        base_url=args.base_url,
        timeout=args.timeout,
    )

    prompt = " ".join(args.prompt)
    if args.command == "generate":
        results = client.generate(
            prompt,
            out_dir=args.out_dir,
            filename_prefix=args.prefix,
            n=args.n,
            size=args.size,
            quality=args.quality,
            output_format=args.output_format,
            background=args.background,
            moderation=args.moderation,
        )
    elif args.command == "edit":
        results = client.edit(
            prompt,
            images=args.image,
            mask=args.mask,
            out_dir=args.out_dir,
            filename_prefix=args.prefix,
            n=args.n,
            size=args.size,
            quality=args.quality,
            output_format=args.output_format,
        )
    else:
        raise ValueError(f"Unsupported command: {args.command}")

    for result in results:
        print(result.path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
