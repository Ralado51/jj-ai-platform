from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from app.models.image_generation_job import ImageGenerationJob
from app.repositories.image_generation_job_repository import ImageGenerationJobRepository
from app.schemas.image_jobs import ImageJobBatchCreate, ImageJobCreate


class ImageGenerationJobService:
    def __init__(self, repository: ImageGenerationJobRepository) -> None:
        self.repository = repository

    def create(self, owner_id: UUID, payload: ImageJobCreate) -> ImageGenerationJob:
        return self.repository.create(
            ImageGenerationJob(owner_id=owner_id, **payload.model_dump())
        )

    def create_batch(
        self, owner_id: UUID, payload: ImageJobBatchCreate
    ) -> list[ImageGenerationJob]:
        jobs = [
            ImageGenerationJob(owner_id=owner_id, **item.model_dump())
            for item in payload.items
        ]
        return self.repository.create_many(jobs)

    def get(self, job_id: UUID, owner_id: UUID) -> ImageGenerationJob:
        job = self.repository.get(job_id=job_id, owner_id=owner_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image job not found.")
        return job

    def review(self, job_id: UUID, owner_id: UUID, action: str) -> ImageGenerationJob:
        job = self.get(job_id=job_id, owner_id=owner_id)
        if action == "regenerate":
            job.status = "pending"
            job.worker_id = None
            job.asset_id = None
            job.error = None
            return self.repository.save(job)

        if job.status != "generated":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only generated jobs can be approved or rejected.",
            )
        job.status = "approved" if action == "approve" else "rejected"
        return self.repository.save(job)
