from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any

import modal

WORKER_DIR = Path(__file__).parent
REMOTE_WORKER_DIR = Path("/opt/jj-image-worker")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "requests>=2.32,<3",
        "torch>=2.5,<3",
        "diffusers>=0.35,<1",
        "transformers>=4.48,<6",
        "accelerate>=1.2,<2",
        "safetensors>=0.5,<1",
        "Pillow>=11,<13",
    )
    .add_local_dir(str(WORKER_DIR), remote_path=str(REMOTE_WORKER_DIR))
)

app = modal.App("jj-free-image-worker")
worker_secret = modal.Secret.from_name("jj-image-worker")
_gpu_worker: Any | None = None


def _load_runner():
    runner_path = REMOTE_WORKER_DIR / "runner.py"
    spec = importlib.util.spec_from_file_location("jj_image_worker_runner", runner_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load worker runner from {runner_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@app.function(
    image=image,
    gpu="T4",
    secrets=[worker_secret],
    timeout=1200,
)
def generate_on_gpu(job: dict[str, Any]) -> tuple[str, int]:
    global _gpu_worker

    os.environ.setdefault("JJ_WORKER_RUNTIME", "modal")
    os.environ.setdefault("JJ_WORKER_NAME", "modal-t4-generator")
    os.environ.setdefault("JJ_IMAGE_MODEL", "stable-diffusion-v1-5/stable-diffusion-v1-5")
    os.environ.setdefault("JJ_IMAGE_STEPS", "20")

    if _gpu_worker is None:
        runner = _load_runner()
        _gpu_worker = runner.JJImageWorker()
    return _gpu_worker.generate(job)


@app.function(
    image=image,
    secrets=[worker_secret],
    schedule=modal.Period(minutes=1),
    timeout=3600,
)
def dispatch() -> dict[str, int]:
    os.environ.setdefault("JJ_WORKER_RUNTIME", "modal")
    os.environ.setdefault("JJ_WORKER_NAME", "modal-dispatcher")
    os.environ.setdefault("JJ_IMAGE_MODEL", "stable-diffusion-v1-5/stable-diffusion-v1-5")

    runner = _load_runner()
    worker = runner.JJImageWorker()
    worker.register()
    worker.heartbeat(force=True)

    max_jobs = max(1, int(os.getenv("JJ_MODAL_MAX_JOBS_PER_TICK", "4")))
    completed = 0
    failed = 0

    for _ in range(max_jobs):
        job = worker.claim()
        if not job:
            break

        print(
            f"Modal claimed job {job['job_id']} "
            f"{job['width']}x{job['height']} model={job['model']}"
        )
        try:
            image_base64, seed = generate_on_gpu.remote(job)
            worker.submit_result(job, image_base64, seed)
            completed += 1
        except Exception as exc:
            worker.submit_failure(job, exc)
            failed += 1

    return {"completed": completed, "failed": failed}


@app.local_entrypoint()
def main() -> None:
    result = dispatch.remote()
    print(result)
