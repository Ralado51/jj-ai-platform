from __future__ import annotations

import base64
import io
import os
import socket
import time
from typing import Any

import requests

API_URL = os.getenv("JJ_API_URL", "https://api.jjnetwork.com.br/api/v1").rstrip("/")
WORKER_TOKEN = os.getenv("JJ_IMAGE_WORKER_TOKEN", "")
WORKER_NAME = os.getenv("JJ_WORKER_NAME", f"image-worker-{socket.gethostname()}")
WORKER_RUNTIME = os.getenv("JJ_WORKER_RUNTIME", "lightning")
MODEL_ID = os.getenv(
    "JJ_IMAGE_MODEL",
    "stable-diffusion-v1-5/stable-diffusion-v1-5",
)
POLL_SECONDS = float(os.getenv("JJ_WORKER_POLL_SECONDS", "10"))
HEARTBEAT_SECONDS = float(os.getenv("JJ_WORKER_HEARTBEAT_SECONDS", "30"))
INFERENCE_STEPS = int(os.getenv("JJ_IMAGE_STEPS", "28"))
GUIDANCE_SCALE = float(os.getenv("JJ_IMAGE_GUIDANCE_SCALE", "7.5"))
HTTP_TIMEOUT = float(os.getenv("JJ_WORKER_HTTP_TIMEOUT", "60"))
HF_TOKEN = os.getenv("HF_TOKEN") or None


class JJImageWorker:
    def __init__(self) -> None:
        if not WORKER_TOKEN:
            raise RuntimeError("JJ_IMAGE_WORKER_TOKEN is required")

        self.session = requests.Session()
        self.session.headers.update({"X-JJ-Worker-Token": WORKER_TOKEN})
        self.worker_id: str | None = None
        self.pipeline: Any | None = None
        self.torch: Any | None = None
        self.last_heartbeat = 0.0

    def request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        response = self.session.request(
            method,
            f"{API_URL}{path}",
            timeout=HTTP_TIMEOUT,
            **kwargs,
        )
        response.raise_for_status()
        return response

    def register(self) -> None:
        response = self.request(
            "POST",
            "/image-workers/register",
            json={
                "name": WORKER_NAME,
                "runtime": WORKER_RUNTIME,
                "model": MODEL_ID,
            },
        )
        payload = response.json()
        self.worker_id = payload["id"]
        self.last_heartbeat = time.monotonic()
        print(
            f"Registered worker {WORKER_NAME} ({self.worker_id}) "
            f"runtime={WORKER_RUNTIME} model={MODEL_ID}"
        )

    def heartbeat(self, force: bool = False) -> None:
        if not self.worker_id:
            return
        now = time.monotonic()
        if not force and now - self.last_heartbeat < HEARTBEAT_SECONDS:
            return
        self.request(
            "POST",
            "/image-workers/heartbeat",
            json={"worker_id": self.worker_id},
        )
        self.last_heartbeat = now

    def claim(self) -> dict[str, Any] | None:
        if not self.worker_id:
            raise RuntimeError("Worker is not registered")
        response = self.request(
            "POST",
            "/image-workers/next-job",
            json={"worker_id": self.worker_id},
        )
        payload = response.json()
        return payload if payload.get("job_id") else None

    def load_pipeline(self) -> None:
        if self.pipeline is not None:
            return

        import torch
        from diffusers import StableDiffusionPipeline

        if not torch.cuda.is_available():
            raise RuntimeError("CUDA GPU is required for the free image worker")

        print(f"Loading {MODEL_ID} on {torch.cuda.get_device_name(0)}...")
        kwargs: dict[str, Any] = {
            "torch_dtype": torch.float16,
            "use_safetensors": True,
        }
        if HF_TOKEN:
            kwargs["token"] = HF_TOKEN

        pipeline = StableDiffusionPipeline.from_pretrained(MODEL_ID, **kwargs)
        pipeline = pipeline.to("cuda")
        pipeline.enable_attention_slicing()

        self.torch = torch
        self.pipeline = pipeline
        print("Image pipeline ready")

    def generate(self, job: dict[str, Any]) -> tuple[str, int]:
        self.load_pipeline()
        assert self.pipeline is not None
        assert self.torch is not None

        requested_seed = job.get("seed")
        seed = int(requested_seed) if requested_seed is not None else int.from_bytes(os.urandom(4), "big")
        generator = self.torch.Generator(device="cuda").manual_seed(seed)

        width = int(job["width"])
        height = int(job["height"])
        if width % 8 or height % 8:
            raise ValueError("Image width and height must be multiples of 8")

        with self.torch.inference_mode():
            result = self.pipeline(
                prompt=job["prompt"],
                width=width,
                height=height,
                num_inference_steps=INFERENCE_STEPS,
                guidance_scale=GUIDANCE_SCALE,
                generator=generator,
            )

        image = result.images[0]
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return encoded, seed

    def submit_result(self, job: dict[str, Any], image_base64: str, seed: int) -> None:
        assert self.worker_id is not None
        self.request(
            "POST",
            f"/image-workers/jobs/{job['job_id']}/result",
            json={
                "worker_id": self.worker_id,
                "image_base64": image_base64,
                "mime_type": "image/png",
                "seed": seed,
            },
        )
        print(f"Completed job {job['job_id']} seed={seed}")

    def submit_failure(self, job: dict[str, Any], exc: Exception) -> None:
        assert self.worker_id is not None
        error = f"{type(exc).__name__}: {exc}"[:12000]
        try:
            self.request(
                "POST",
                f"/image-workers/jobs/{job['job_id']}/failed",
                json={"worker_id": self.worker_id, "error": error},
            )
        finally:
            print(f"Failed job {job['job_id']}: {error}")

    def run(self) -> None:
        self.register()
        while True:
            try:
                self.heartbeat()
                job = self.claim()
                if not job:
                    time.sleep(POLL_SECONDS)
                    continue

                print(
                    f"Claimed job {job['job_id']} "
                    f"{job['width']}x{job['height']} model={job['model']}"
                )
                try:
                    image_base64, seed = self.generate(job)
                    self.submit_result(job, image_base64, seed)
                except Exception as exc:
                    self.submit_failure(job, exc)
            except requests.RequestException as exc:
                print(f"JJ API unavailable: {exc}; retrying in {POLL_SECONDS}s")
                time.sleep(POLL_SECONDS)
            except KeyboardInterrupt:
                print("Worker stopped")
                return


if __name__ == "__main__":
    JJImageWorker().run()
