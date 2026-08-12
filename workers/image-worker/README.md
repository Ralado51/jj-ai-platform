# JJ Free Image Worker

Pull-based GPU worker for persistent image jobs in JJ AI Platform.

The worker does not expose ports and does not require a public URL. It registers itself in the JJ API, polls for compatible jobs, generates the image locally on a CUDA GPU, and returns the PNG as Base64. The backend stores the result in S3/MinIO and sends the job to Human Review.

## Initial engine

The MVP uses `stable-diffusion-v1-5/stable-diffusion-v1-5` with Diffusers in FP16. This is intentionally a lightweight baseline for free T4/P100-class runtimes. The worker protocol is model-agnostic, so higher-quality engines can be added later without changing Image Jobs or Human Review.

## Runtime requirements

- Python 3.10+
- NVIDIA CUDA GPU
- PyTorch with CUDA support
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

## Generic CUDA worker

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

## Kaggle worker

Kaggle uses the same runner and therefore the same JJ queue and Human Review flow.

1. Create a Kaggle Notebook and enable a GPU accelerator.
2. Enable Internet access for the notebook so it can reach the JJ API and Hugging Face Hub.
3. Add a Kaggle secret named `JJ_IMAGE_WORKER_TOKEN` with the same worker token configured in the JJ backend.
4. Optionally add `HF_TOKEN`.
5. Clone the repository and install the worker dependencies:

```bash
git clone https://github.com/Ralado51/jj-ai-platform.git
cd jj-ai-platform
pip install -r workers/image-worker/requirements.txt
```

6. Start the Kaggle adapter:

```bash
python workers/image-worker/kaggle_entrypoint.py
```

The adapter reads credentials from `kaggle_secrets`, identifies itself with runtime `kaggle`, and then starts the standard pull loop. Stop the notebook session when it is not processing jobs so GPU quota is not consumed while idle.

## Modal worker

Modal uses a different execution pattern to avoid allocating a GPU just to poll an empty queue:

```text
Modal scheduled CPU dispatcher
        -> register / claim on JJ
        -> if no job: exit
        -> if job exists: invoke T4 function
        -> generate image
        -> submit result/failure to JJ
```

The dispatcher runs every minute and processes up to four jobs per tick by default. The T4 function is only called after a compatible job has been claimed.

Install the Modal CLI locally:

```bash
pip install -r workers/image-worker/modal-requirements.txt
modal setup
```

Create a Modal secret named `jj-image-worker` containing at least:

```text
JJ_IMAGE_WORKER_TOKEN=<same token configured in JJ>
```

Optional keys in the same secret:

```text
HF_TOKEN=...
JJ_API_URL=https://api.jjnetwork.com.br/api/v1
JJ_IMAGE_MODEL=stable-diffusion-v1-5/stable-diffusion-v1-5
JJ_IMAGE_STEPS=20
JJ_IMAGE_GUIDANCE_SCALE=7.5
JJ_MODAL_MAX_JOBS_PER_TICK=4
```

Test one dispatch manually:

```bash
modal run workers/image-worker/modal_app.py
```

Deploy the scheduled worker:

```bash
modal deploy workers/image-worker/modal_app.py
```

After deployment, Modal invokes the CPU dispatcher every minute. GPU usage only begins when the dispatcher finds a compatible pending Image Job.

## Job routing

A worker only claims pending jobs whose `model` exactly matches the model registered by that worker. This prevents a worker from generating an image with a different engine while the Image Job retains incorrect model metadata.

## Free compute pool

The JJ provider remains `free-worker`. Runtime is an implementation detail and can be any compatible worker:

- Lightning AI
- Kaggle
- Modal
- Google Colab
- any temporary CUDA host

Multiple workers can coexist. The JJ API remains the queue and source of truth, while Image Review remains the human approval gate.
