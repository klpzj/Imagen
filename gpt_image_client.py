from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from PIL import Image


DEFAULT_MODEL = "gpt-image-2"
DEFAULT_SIZE = "1024x1024"
DEFAULT_QUALITY = "auto"
DEFAULT_OUTPUT_FORMAT = "png"
DEFAULT_BASE_URL = "http://149.248.37.38:8080/"

# Extensions are image-body values, not another source of request authority.
RESERVED_IMAGE_FIELDS = frozenset({
    "model", "prompt", "n", "size", "quality", "output_format", "background",
    "moderation", "output_compression", "response_format", "input_fidelity", "style",
    "image", "images", "image_ids", "source_order", "mask", "stream", "partial_images",
    "user", "timeout", "api_key", "API_KEY", "base_url", "headers", "extra_headers",
    "extra_query", "extra_body", "auth_file", "out_dir", "output_dir", "filename_prefix",
})


def validate_extra_body(values: dict[str, Any]) -> None:
    conflict = RESERVED_IMAGE_FIELDS.intersection(values)
    if conflict:
        raise ValueError(f"扩展参数不能覆盖专用字段或服务设置：{', '.join(sorted(conflict))}。")


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
            max_retries=0,
            **({"timeout": timeout} if timeout is not None else {}),
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
        output_compression: int | None = None,
        style: str | None = None,
        response_format: str | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> list[ImageResult]:
        """Generate one or more images from text and save them locally."""

        self._validate_prompt(prompt)
        params = self._image_parameters(
            prompt, n=n, size=size, quality=quality, output_format=output_format,
            background=background, output_compression=output_compression,
            response_format=response_format, extra_body=extra_body,
        )
        if moderation and moderation != "none":
            params["moderation"] = moderation
        if style:
            params["style"] = style

        response = self.client.images.generate(**params)
        return self._save_response_images(
            response,
            out_dir=out_dir,
            filename_prefix=filename_prefix or _slugify(prompt),
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
        moderation: str | None = "none",
        background: str | None = None,
        output_compression: int | None = None,
        input_fidelity: str | None = None,
        response_format: str | None = None,
        extra_body: dict[str, Any] | None = None,
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
            params = self._image_parameters(
                prompt, n=n, size=size, quality=quality, output_format=output_format,
                background=background, output_compression=output_compression,
                response_format=response_format, extra_body=extra_body,
            )
            params["image"] = opened_images[0] if len(opened_images) == 1 else opened_images
            if opened_mask:
                params["mask"] = opened_mask
            if input_fidelity:
                params["input_fidelity"] = input_fidelity
            if moderation and moderation != "none":
                params.setdefault("extra_body", {})["moderation"] = moderation

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
        )

    def _image_parameters(
        self, prompt: str, *, n: int, size: str, quality: str, output_format: str,
        background: str | None, output_compression: int | None,
        response_format: str | None, extra_body: dict[str, Any] | None,
    ) -> dict[str, Any]:
        validate_extra_body(extra_body or {})
        params: dict[str, Any] = {
            "model": self.model, "prompt": prompt, "n": n, "size": size,
            "quality": quality, "output_format": output_format,
        }
        if background:
            if background == "transparent" and output_format == "jpeg":
                raise ValueError("JPEG 无法保存透明背景。")
            params["background"] = background
        if output_compression is not None and output_format in {"jpeg", "webp"}:
            params["output_compression"] = output_compression
        if response_format:
            params["response_format"] = response_format
        if extra_body:
            params["extra_body"] = dict(extra_body)
        return params

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
    ) -> list[ImageResult]:
        target_dir = Path(out_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        data = getattr(response, "data", None)
        if not data:
            raise RuntimeError("Image API returned no image data.")

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        batch_id = uuid4().hex[:8]
        results: list[ImageResult] = []

        for index, item in enumerate(data, start=1):
            b64_json = getattr(item, "b64_json", None)
            url = getattr(item, "url", None)

            if b64_json:
                image_bytes = base64.b64decode(b64_json)
            elif url:
                with urllib.request.urlopen(url, timeout=60) as response_stream:
                    image_bytes = response_stream.read()
            else:
                raise RuntimeError("Image item did not include b64_json or url.")

            with Image.open(io.BytesIO(image_bytes)) as image:
                actual_format = (image.format or "").lower()
                image.verify()
            if actual_format not in {"png", "jpeg", "webp"}:
                raise RuntimeError("Image API returned an unsupported image format.")
            extension = _normalize_extension(actual_format)
            path = target_dir / f"{filename_prefix}-{timestamp}-{batch_id}-{index}.{extension}"
            path.write_bytes(image_bytes)

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
    _add_common_image_args(generate_parser)
    generate_parser.add_argument("--style", default=None, help="Optional model-supported style.")
    generate_parser.add_argument("prompt", nargs="+", help="Prompt text.")

    edit_parser = subparsers.add_parser("edit", help="Edit images from text.")
    _add_common_image_args(edit_parser)
    edit_parser.add_argument("--input-fidelity", default=None, help="Optional input fidelity, e.g. low or high.")
    edit_parser.add_argument("--image", action="append", required=True, help="Input image path.")
    edit_parser.add_argument("--mask", default=None, help="Optional mask image path.")
    edit_parser.add_argument("prompt", nargs="+", help="Edit instruction.")

    return parser


def _parse_extra_body(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            raise ValueError("Extension parameters must be a JSON object.")
        validate_extra_body(parsed)
        return parsed
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _add_common_image_args(parser: argparse.ArgumentParser) -> None:
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
    parser.add_argument("--background", default=None, help="Optional background, e.g. auto, transparent, or opaque.")
    parser.add_argument("--output-compression", type=int, default=None, help="JPEG/WebP compression, 0-100.")
    parser.add_argument("--response-format", default=None, help="Optional response form, e.g. b64_json or url.")
    parser.add_argument("--extra-body", type=_parse_extra_body, default=None, help="Additional image parameters as a JSON object.")
    parser.add_argument(
        "--moderation",
        default="none",
        help="Image moderation, e.g. auto or low. none omits the parameter (service default).",
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
            output_compression=args.output_compression,
            style=args.style,
            response_format=args.response_format,
            extra_body=args.extra_body,
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
            moderation=args.moderation,
            background=args.background,
            output_compression=args.output_compression,
            input_fidelity=args.input_fidelity,
            response_format=args.response_format,
            extra_body=args.extra_body,
        )
    else:
        raise ValueError(f"Unsupported command: {args.command}")

    for result in results:
        print(result.path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
