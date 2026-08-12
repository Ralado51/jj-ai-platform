from __future__ import annotations

import importlib.util
import os
import socket
from pathlib import Path


def _load_secret(name: str, *, required: bool = False) -> str | None:
    from kaggle_secrets import UserSecretsClient

    try:
        value = UserSecretsClient().get_secret(name)
    except Exception:
        value = None
    if required and not value:
        raise RuntimeError(f"Kaggle secret {name} is required")
    return value


def _load_runner():
    runner_path = Path(__file__).with_name("runner.py")
    spec = importlib.util.spec_from_file_location("jj_image_worker_runner", runner_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load worker runner from {runner_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    os.environ["JJ_IMAGE_WORKER_TOKEN"] = _load_secret("JJ_IMAGE_WORKER_TOKEN", required=True) or ""
    hf_token = _load_secret("HF_TOKEN")
    if hf_token:
        os.environ["HF_TOKEN"] = hf_token

    os.environ.setdefault("JJ_API_URL", "https://api.jjnetwork.com.br/api/v1")
    os.environ.setdefault("JJ_WORKER_RUNTIME", "kaggle")
    os.environ.setdefault("JJ_WORKER_NAME", f"kaggle-{socket.gethostname()}")
    os.environ.setdefault("JJ_IMAGE_MODEL", "stable-diffusion-v1-5/stable-diffusion-v1-5")
    os.environ.setdefault("JJ_IMAGE_STEPS", "20")

    runner = _load_runner()
    runner.JJImageWorker().run()


if __name__ == "__main__":
    main()
