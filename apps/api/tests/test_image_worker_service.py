from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.models.image_generation_job import ImageGenerationJob
from app.models.image_worker import ImageWorker
from app.schemas.image_workers import ImageWorkerRegisterRequest
from app.services.image_worker_service import ImageWorkerService


class FakeImageWorkerRepository:
    def __init__(self) -> None:
        self.worker = ImageWorker(
            id=uuid4(),
            name="lightning-1",
            runtime="lightning",
            model="Z-Image-Turbo",
            status="online",
            last_seen_at=datetime.now(timezone.utc),
        )
        self.job = ImageGenerationJob(
            id=uuid4(),
            owner_id=uuid4(),
            project_id=uuid4(),
            external_id="hero-home",
            provider="free-worker",
            model="Z-Image-Turbo",
            prompt="premium healthcare editorial photo",
            width=1344,
            height=768,
            status="pending",
        )

    def register(self, name: str, runtime: str, model: str) -> ImageWorker:
        self.worker.name = name
        self.worker.runtime = runtime
        self.worker.model = model
        return self.worker

    def get(self, worker_id):
        return self.worker if worker_id == self.worker.id else None

    def heartbeat(self, worker: ImageWorker) -> ImageWorker:
        worker.last_seen_at = datetime.now(timezone.utc)
        return worker

    def claim_next_job(
        self,
        worker: ImageWorker,
        runtime_priority: tuple[str, ...] = (),
        online_timeout_seconds: int = 90,
        max_active_jobs: int = 1,
    ):
        if self.job.status != "pending":
            return None
    
        self.job.status = "processing"
        self.job.worker_id = str(worker.id)
        return self.job
        
    def get_claimed_job(self, job_id, worker_id):
        if (
            job_id == self.job.id
            and self.job.worker_id == str(worker_id)
            and self.job.status == "processing"
        ):
            return self.job
        return None

    def complete_job(self, job, asset):
        asset.id = uuid4()
        job.asset_id = asset.id
        job.status = "generated"
        job.error = None
        return job

    def fail_job(self, job, error: str):
        job.status = "failed"
        job.error = error
        return job


def make_service() -> tuple[ImageWorkerService, FakeImageWorkerRepository]:
    repository = FakeImageWorkerRepository()
    settings = Settings(
        image_worker_token="test-worker-secret",
        s3_public_endpoint_url="https://files.example.com",
        s3_bucket="jj-ai-projects",
    )
    service = ImageWorkerService(repository, settings)
    service._upload = lambda storage_path, data, mime_type: None
    return service, repository


def test_register_claim_and_complete_job() -> None:
    service, repository = make_service()
    worker = service.register(
        ImageWorkerRegisterRequest(
            name="colab-1",
            runtime="colab",
            model="Z-Image-Turbo",
        )
    )

    job = service.claim_next_job(worker.id)
    assert job is not None
    assert job.status == "processing"
    assert job.worker_id == str(worker.id)

    completed = service.complete_job(
        job_id=job.id,
        worker_id=worker.id,
        image_base64="aW1hZ2UtYnl0ZXM=",
        mime_type="image/png",
        seed=23456,
    )

    assert completed.status == "generated"
    assert completed.asset_id is not None
    assert completed.seed == 23456
    assert repository.job.error is None


def test_failed_job_is_recorded() -> None:
    service, repository = make_service()
    service.claim_next_job(repository.worker.id)

    failed = service.fail_job(
        repository.job.id,
        repository.worker.id,
        "GPU runtime disconnected",
    )

    assert failed.status == "failed"
    assert failed.error == "GPU runtime disconnected"


def test_invalid_base64_is_rejected() -> None:
    service, repository = make_service()
    service.claim_next_job(repository.worker.id)

    with pytest.raises(HTTPException) as exc:
        service.complete_job(
            job_id=repository.job.id,
            worker_id=repository.worker.id,
            image_base64="not-base64!",
            mime_type="image/png",
            seed=None,
        )

    assert exc.value.status_code == 422


def test_other_worker_cannot_complete_claimed_job() -> None:
    service, repository = make_service()
    service.claim_next_job(repository.worker.id)

    with pytest.raises(HTTPException) as exc:
        service.complete_job(
            job_id=repository.job.id,
            worker_id=uuid4(),
            image_base64="aW1hZ2U=",
            mime_type="image/png",
            seed=None,
        )

    assert exc.value.status_code == 409
