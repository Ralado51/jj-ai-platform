from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.schemas.image_jobs import ImageJobBatchCreate, ImageJobCreate
from app.services.image_generation_job_service import ImageGenerationJobService


class FakeRepository:
    def __init__(self) -> None:
        self.jobs: dict = {}

    def _ensure_id(self, job):
        if job.id is None:
            job.id = uuid4()
        return job

    def create(self, job):
        job = self._ensure_id(job)
        self.jobs[job.id] = job
        return job

    def create_many(self, jobs):
        for job in jobs:
            self.create(job)
        return jobs

    def get(self, job_id, owner_id):
        job = self.jobs.get(job_id)
        if job and job.owner_id == owner_id:
            return job
        return None

    def save(self, job):
        self.jobs[job.id] = job
        return job


def make_payload(project_id):
    return ImageJobCreate(
        project_id=project_id,
        external_id="elo-hero",
        prompt="Editorial healthcare photo",
    )


def test_create_and_batch_jobs_start_pending():
    repo = FakeRepository()
    service = ImageGenerationJobService(repo)
    owner_id = uuid4()
    project_id = uuid4()

    single = service.create(owner_id, make_payload(project_id))
    batch = service.create_batch(
        owner_id,
        ImageJobBatchCreate(items=[make_payload(project_id), make_payload(project_id)]),
    )

    assert single.status == "pending"
    assert len(batch) == 2
    assert all(job.status == "pending" for job in batch)


def test_review_requires_generated_and_regenerate_resets_job():
    repo = FakeRepository()
    service = ImageGenerationJobService(repo)
    owner_id = uuid4()
    job = service.create(owner_id, make_payload(uuid4()))

    with pytest.raises(HTTPException) as exc:
        service.review(job.id, owner_id, "approve")
    assert exc.value.status_code == 409

    job.status = "generated"
    job.worker_id = "worker-1"
    job.asset_id = uuid4()
    approved = service.review(job.id, owner_id, "approve")
    assert approved.status == "approved"

    regenerated = service.review(job.id, owner_id, "regenerate")
    assert regenerated.status == "pending"
    assert regenerated.worker_id is None
    assert regenerated.asset_id is None
