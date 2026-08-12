from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.image_generation_job import ImageGenerationJob


class ImageGenerationJobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, job: ImageGenerationJob) -> ImageGenerationJob:
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def create_many(self, jobs: list[ImageGenerationJob]) -> list[ImageGenerationJob]:
        self.db.add_all(jobs)
        self.db.commit()
        for job in jobs:
            self.db.refresh(job)
        return jobs

    def get(self, job_id: UUID, owner_id: UUID) -> ImageGenerationJob | None:
        stmt = select(ImageGenerationJob).where(
            ImageGenerationJob.id == job_id,
            ImageGenerationJob.owner_id == owner_id,
        )
        return self.db.scalar(stmt)

    def list(
        self,
        owner_id: UUID,
        status: str | None = None,
        project_id: UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[ImageGenerationJob]:
        stmt = select(ImageGenerationJob).where(ImageGenerationJob.owner_id == owner_id)
        if status:
            stmt = stmt.where(ImageGenerationJob.status == status)
        if project_id:
            stmt = stmt.where(ImageGenerationJob.project_id == project_id)
        stmt = stmt.order_by(ImageGenerationJob.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def save(self, job: ImageGenerationJob) -> ImageGenerationJob:
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job
