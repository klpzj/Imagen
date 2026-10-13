"""Exercise HTTP -> services -> real SDK serialization, without network or user data."""
from __future__ import annotations

import base64
import io
import json
import unittest
from contextlib import ExitStack
from dataclasses import replace
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from openai import OpenAI
from PIL import Image

from backend import config, image_service, image_store, job_store
from backend.app import app
from backend.schemas import GenerateRequest, ImageRecord


def image_bytes(mode="RGBA", size=(24, 16), format="PNG"):
    buffer = io.BytesIO()
    Image.new(mode, size).save(buffer, format=format)
    return buffer.getvalue()


class ImageParameterContractTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(TemporaryDirectory(prefix="imagen-test-")))
        self.settings = config.BackendSettings(
            api_key="synthetic-test-key", base_url="https://images.example.invalid/v1/",
            default_model="configured-test-model", auth_path=self.root / "missing-auth.json",
            outputs_dir=self.root, manifest_path=self.root / "manifest.json",
        )
        for module in (config, image_service, job_store):
            self.stack.enter_context(patch.object(module, "get_backend_settings", return_value=self.settings))
        self.stack.enter_context(patch.object(config, "get_model_candidates", return_value=(self.settings.default_model,)))
        for module in (image_store, job_store):
            self.stack.enter_context(patch.object(module, "OUTPUTS_DIR", self.root))
        # The store's default path arguments are bound at import time.
        read_manifest, write_manifest = image_store._read_manifest, image_store._write_manifest
        read_jobs, write_jobs = job_store._read_jobs, job_store._write_jobs
        self.stack.enter_context(patch.object(image_store, "_read_manifest", side_effect=lambda: read_manifest(self.root / "manifest.json")))
        self.stack.enter_context(patch.object(image_store, "_write_manifest", side_effect=lambda records: write_manifest(records, self.root / "manifest.json")))
        self.stack.enter_context(patch.object(job_store, "_read_jobs", side_effect=lambda: read_jobs(self.root / "jobs.json")))
        self.stack.enter_context(patch.object(job_store, "_write_jobs", side_effect=lambda jobs: write_jobs(jobs, self.root / "jobs.json")))
        self.stack.enter_context(patch.object(image_service._LOGGER, "exception"))
        self.requests = []
        self.client_arguments = []
        self.failure = None
        self.output_bytes = image_bytes()
        self.use_url = False
        self.stack.enter_context(patch("openai.OpenAI", side_effect=self.make_sdk))
        self.http = self.stack.enter_context(TestClient(app))

    def make_sdk(self, **kwargs):
        self.client_arguments.append(kwargs)
        transport = httpx.MockTransport(self.respond)
        client = OpenAI(**kwargs, http_client=httpx.Client(transport=transport))
        self.stack.callback(client.close)
        return client

    def respond(self, request):
        self.assertEqual(request.url.host, "images.example.invalid")
        content = request.read()
        if "multipart/form-data" in request.headers["content-type"]:
            message = BytesParser(policy=policy.default).parsebytes(
                f"Content-Type: {request.headers['content-type']}\r\n\r\n".encode() + content
            )
            fields, files = {}, []
            for part in message.iter_parts():
                name = part.get_param("name", header="content-disposition")
                payload = part.get_payload(decode=True)
                if part.get_filename():
                    files.append((name, payload))
                else:
                    fields[name] = payload.decode()
        else:
            fields, files = json.loads(content), []
        self.requests.append((request.url.path, fields, files))
        if self.failure:
            return httpx.Response(400, json={"error": self.failure})
        item = {"url": "https://images.example.invalid/result"} if self.use_url else {
            "b64_json": base64.b64encode(self.output_bytes).decode(),
            "revised_prompt": "Synthetic revised prompt",
        }
        return httpx.Response(200, json={"created": 0, "data": [item] * int(fields.get("n", 1))})

    def generate(self, options=None, route="/api/generate", prompt="Synthetic prompt"):
        return self.http.post(route, json={"prompt": prompt, "options": options or {}})

    def edit(self, options=None, mask=None, source=None, extra_files=None):
        files = [("images", ("upload.png", source or image_bytes(), "image/png"))]
        if mask is not None:
            files.append(("mask", ("mask.png", mask, "image/png")))
        files.extend(extra_files or [])
        return self.http.post("/api/edit", data={"prompt": "Synthetic edit", **(options or {})}, files=files)

    def test_generation_custom_values_and_zero_survive_sdk_and_history(self):
        options = {
            "model": "custom-image-model", "size": "1536x864", "quality": "custom-quality",
            "output_format": "webp", "background": "custom-background", "moderation": "custom-moderation",
            "n": 2, "output_compression": 0, "style": "custom-style",
            "response_format": "custom-response", "timeout": 12.5,
            "extra_body": {"seed": 0, "watermark": False},
        }
        response = self.generate(options)
        self.assertEqual(response.status_code, 200, response.text)
        records = response.json()["images"]
        self.assertEqual(len(records), 2)
        path, sent, files = self.requests[0]
        expected = {key: value for key, value in options.items() if key not in {"timeout", "extra_body"}}
        self.assertEqual(path, "/v1/images/generations")
        self.assertEqual(sent, {**expected, "prompt": "Synthetic prompt", "seed": 0, "watermark": False})
        self.assertEqual(files, [])
        self.assertEqual(self.client_arguments[0]["timeout"], 12.5)
        self.assertEqual(self.client_arguments[0]["max_retries"], 0)
        for record in records:
            self.assertEqual(record["options"], options)
            self.assertEqual(record["format"], "png")  # Actual bytes win over the requested format.
            with Image.open(self.root / record["filename"]) as image:
                self.assertEqual(image.format, "PNG")
        self.assertEqual(self.http.get("/api/images").json()["images"][0]["options"], options)

    def test_defaults_are_omitted_and_png_keeps_compression_out_of_request(self):
        response = self.generate({"moderation": "none", "output_compression": 0})
        self.assertEqual(response.status_code, 200, response.text)
        options = response.json()["images"][0]["options"]
        self.assertEqual(options, {"model": self.settings.default_model, "size": "1024x1024", "quality": "auto", "output_format": "png", "n": 1})
        sent = self.requests[0][1]
        for field in ("background", "moderation", "output_compression", "style", "response_format", "extra_body"):
            self.assertNotIn(field, sent)
        self.assertNotIn("timeout", self.client_arguments[0])

    def test_edit_parameters_mask_and_mixed_input_order(self):
        filename = "history.png"
        (self.root / filename).write_bytes(image_bytes(size=(24, 16)))
        record = ImageRecord(
            id="history-1", type="generate", filename=filename, url=f"/outputs/{filename}",
            prompt="Synthetic history", model="old-model", size="24x16", quality="auto", format="png",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        image_store.add_records([record])
        options = {
            "model": "custom-edit-model", "size": "auto", "quality": "custom-quality",
            "output_format": "jpeg", "background": "opaque", "output_compression": "0",
            "moderation": "low", "input_fidelity": "custom-fidelity", "response_format": "b64_json",
            "timeout": "8.5", "extra_body": '{"seed":0,"watermark":false}', "n": "1",
            "image_ids": "history-1", "upload_ids": "upload-1",
            "source_order": ["history:history-1", "upload:upload-1"],
        }
        response = self.edit(options, mask=image_bytes(), source=image_bytes("RGB", (32, 20), "JPEG"))
        self.assertEqual(response.status_code, 200, response.text)
        path, sent, files = self.requests[0]
        self.assertEqual(path, "/v1/images/edits")
        for key, value in {
            "model": "custom-edit-model", "size": "auto", "quality": "custom-quality", "output_format": "jpeg",
            "background": "opaque", "output_compression": "0", "moderation": "low",
            "input_fidelity": "custom-fidelity", "response_format": "b64_json", "seed": "0", "watermark": "false",
        }.items():
            self.assertEqual(sent[key], value)
        source_files = [payload for name, payload in files if name.startswith("image")]
        self.assertEqual([Image.open(io.BytesIO(payload)).size for payload in source_files], [(24, 16), (32, 20)])
        self.assertEqual([payload for name, payload in files if name == "mask"], [image_bytes()])
        saved = response.json()["images"][0]
        self.assertEqual(saved["source_order"], ["history:history-1", "upload:upload.png"])
        self.assertEqual(saved["mask_filename"], "mask.png")
        self.assertEqual(saved["options"]["output_compression"], 0)
        self.assertEqual(saved["options"]["extra_body"], {"seed": 0, "watermark": False})
        self.assertEqual(self.client_arguments[0]["timeout"], 8.5)

    def test_invalid_masks_and_images_fail_before_sdk(self):
        for mask in (
            b"not an image", image_bytes("RGB"), image_bytes(size=(12, 16)),
            image_bytes("RGBA", format="TIFF"), image_bytes() + b"\0" * (4 * 1024 * 1024),
        ):
            with self.subTest(mask_length=len(mask)):
                response = self.edit(mask=mask)
                self.assertEqual(response.status_code, 400, response.text)
                self.assertIn("mask", response.json()["detail"]["fields"])
        response = self.edit(source=b"not an image")
        self.assertEqual(response.status_code, 400)
        self.assertIn("images", response.json()["detail"]["fields"])
        self.assertEqual(self.requests, [])

    def test_json_and_multipart_share_field_validation(self):
        for options, field in (
            ({"size": "16:9"}, "size"), ({"n": 3}, "n"), ({"n": 1.5}, "n"),
            ({"output_compression": 101}, "output_compression"), ({"timeout": 0}, "timeout"),
            ({"output_format": "gif"}, "output_format"),
            ({"output_format": "jpeg", "background": "transparent"}, "background"),
        ):
            with self.subTest(options=options):
                for response in (self.generate(options), self.edit(options)):
                    self.assertEqual(response.status_code, 422, response.text)
                    self.assertIn(field, response.json()["detail"]["fields"])
        self.assertEqual(self.generate({"n": True}).status_code, 422)
        for prompt in ("   ", "x" * (config.MAX_PROMPT_LENGTH + 1)):
            response = self.generate(prompt=prompt)
            self.assertEqual(response.status_code, 422)
            self.assertIn("prompt", response.json()["detail"]["fields"])
        self.assertEqual(self.requests, [])

    def test_extensions_cannot_override_image_or_service_fields(self):
        for key in ("model", "n", "background", "prompt", "mask", "api_key", "base_url", "stream", "timeout"):
            with self.subTest(key=key):
                value = {key: "synthetic-override"}
                for response in (self.generate({"extra_body": value}), self.edit({"extra_body": json.dumps(value)})):
                    self.assertEqual(response.status_code, 422, response.text)
                    self.assertIn("extra_body", response.json()["detail"]["fields"])
        for value in ("{", "[]", "null"):
            response = self.edit({"extra_body": value})
            self.assertEqual(response.status_code, 422)
            self.assertIn("extra_body", response.json()["detail"]["fields"])
        self.assertEqual(self.requests, [])

    def test_operation_specific_fields_are_not_silently_ignored(self):
        response = self.generate({"input_fidelity": "high"})
        self.assertEqual(response.status_code, 422)
        self.assertIn("input_fidelity", response.json()["detail"]["fields"])
        self.assertEqual(self.requests, [])

    def test_persisted_job_executes_its_snapshot(self):
        request = GenerateRequest(prompt="Original prompt", options={"quality": "custom-quality"})
        job = job_store.create_generation_job(request)
        self.assertIsNone(request.options.model)
        request.prompt = "Changed prompt"
        request.options.quality = "changed-quality"
        changed = replace(self.settings, default_model="changed-default-model")
        with patch.object(image_service, "get_backend_settings", return_value=changed):
            job_store.run_generation_job(job.id)
        stored = job_store.get_job(job.id)
        self.assertEqual(stored.status, "succeeded")
        self.assertEqual(self.requests[0][1]["prompt"], "Original prompt")
        self.assertEqual(self.requests[0][1]["quality"], "custom-quality")
        self.assertEqual(self.requests[0][1]["model"], self.settings.default_model)
        self.assertEqual(stored.images[0].options, stored.options)

    def test_jobs_reject_concurrent_submission_and_accept_after_completion(self):
        job = job_store.create_generation_job(GenerateRequest(prompt="First prompt"))
        response = self.generate(route="/api/jobs")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["code"], "job_busy")
        self.assertEqual(len(job_store.list_jobs()), 1)
        job_store.run_generation_job(job.id)
        response = self.generate({"size": "1536x864"}, route="/api/jobs")
        self.assertEqual(response.status_code, 200, response.text)
        stored = self.http.get(f"/api/jobs/{response.json()['job']['id']}").json()["job"]
        self.assertEqual(stored["status"], "succeeded")
        self.assertEqual(stored["options"]["size"], "1536x864")

    def test_provider_error_preserves_fields_and_never_retries(self):
        self.failure = {"message": "Synthetic unsupported quality", "param": "quality", "code": "invalid_quality"}
        response = self.generate({"quality": "custom-quality"}, route="/api/jobs")
        self.assertEqual(response.status_code, 200)
        stored = job_store.get_job(response.json()["job"]["id"])
        self.assertEqual(stored.status, "failed")
        self.assertEqual(stored.options["quality"], "custom-quality")
        self.assertIn("quality", stored.error_fields)
        self.assertIn("invalid_quality", stored.error)
        self.assertEqual(len(self.requests), 1)

    def test_old_records_and_jobs_remain_readable(self):
        old = {
            "id": "old-image", "type": "generate", "filename": "old.png", "url": "/outputs/old.png",
            "prompt": "Synthetic old prompt", "model": "old-model", "size": "1024x1024", "quality": "auto",
            "format": "png", "moderation": "none", "created_at": "2026-01-01T00:00:00+00:00",
        }
        (self.root / "manifest.json").write_text(json.dumps([old]), encoding="utf-8")
        response = self.http.get("/api/images")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("options", response.json()["images"][0])
        (self.root / "jobs.json").write_text(json.dumps([{
            "id": "old-job", "status": "failed", "prompt": "Old job", "options": {"moderation": "none"},
            "created_at": old["created_at"], "updated_at": old["created_at"], "error": "Synthetic failure",
        }]), encoding="utf-8")
        response = self.http.get("/api/jobs")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["jobs"][0]["error_fields"], {})

    def test_url_response_uses_actual_format_and_batches_do_not_overwrite(self):
        self.use_url = True
        self.output_bytes = image_bytes("RGB", format="JPEG")
        with patch("gpt_image_client.urllib.request.urlopen", side_effect=lambda *args, **kwargs: io.BytesIO(self.output_bytes)):
            first = self.generate().json()["images"][0]
            second = self.generate().json()["images"][0]
        self.assertEqual(first["format"], "jpeg")
        self.assertNotEqual(first["filename"], second["filename"])
        self.assertEqual((self.root / first["filename"]).read_bytes(), self.output_bytes)
        self.assertEqual((self.root / second["filename"]).read_bytes(), self.output_bytes)

    def test_config_contains_suggestions_and_no_connection_settings(self):
        response = self.http.get("/api/config")
        self.assertEqual(response.status_code, 200)
        config_data = response.json()
        self.assertIn("auto", config_data["sizes"])
        self.assertEqual(config_data["max_n"], config.MAX_N)
        self.assertEqual(config_data["max_prompt_length"], config.MAX_PROMPT_LENGTH)
        for field in ("api_key", "base_url", "auth_path", "outputs_dir"):
            self.assertNotIn(field, config_data)


if __name__ == "__main__":
    unittest.main()
