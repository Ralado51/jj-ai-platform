# JJ Free Image Worker

Pull-based GPU worker for persistent image jobs in JJ AI Platform.

The worker does not expose ports and does not require a public URL. It registers itself in the JJ API, polls for compatible jobs, generates the image locally on a CUDA GPU, and returns the PNG as Base64. The backend stores the result in S3/MinIO and sends the job to Human Review.

## Initial engine

The MVP uses `stable-diffusion-v1-5/stable-diffusion-v1-5` with Diffusers in FP16. This is intentionally a lightweight baseline for free Tesla T4-class runtimes. The worker protocol is model-agnostic, so higher-quality engines can be added later without changing Image Jobs or Human Review.

## Runtime requirements

- Python 3.10+
- NVIDIA CUDA GPU
- PyTorch with CUDA support already installed by the GPU runtime
- outbound HTTPS access to the JJ API and Hugging Face Hub

Install the worker-only dependencies:

```bash
pip install -r workers/image-worker/requirements.txt
```

## Environment

Required:

```bash
export JJ_IMAGE_WORKER_TOKEN="..."
```

Optional:

```bash
export JJ_API_URL="https://api.jjnetwork.com.br/api/v1"
export JJ_WORKER_NAME="lightning-t4-01"
export JJ_WORKER_RUNTIME="lightning"
export JJ_IMAGE_MODEL="stable-diffusion-v1-5/stable-diffusion-v1-5"
export JJ_WORKER_POLL_SECONDS="10"
export JJ_WORKER_HEARTBEAT_SECONDS="30"
export JJ_IMAGE_STEPS="28"
export JJ_IMAGE_GUIDANCE_SCALE="7.5"
export HF_TOKEN="hf_..."
```

The Hugging Face token is optional for public models, but useful for Hub rate limits.

## Run

From the repository root:

```bash
python workers/image-worker/runner.py
```

Expected startup:

```text
Registered worker lightning-t4-01 (...) runtime=lightning model=stable-diffusion-v1-5/stable-diffusion-v1-5
Loading stable-diffusion-v1-5/stable-diffusion-v1-5 on Tesla T4...
Image pipeline ready
```

The model is loaded lazily only after the worker claims its first compatible job, so an idle GPU session does not download model weights unnecessarily.

## Job routing

A worker only claims pending jobs whose `model` exactly matches the model registered by that worker. This prevents a worker from generating an image with a different engine while the Image Job retains incorrect model metadata.

## Free compute targets

The same runner can be used on Lightning AI, Kaggle, Colab, or any temporary CUDA machine. Only `JJ_WORKER_RUNTIME` and `JJ_WORKER_NAME` need to change. The JJ API remains the queue and source of truth.
