from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.image_generation_job import ImageGenerationJob
from app.models.image_worker import ImageWorker


class ImageWorkerRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def register(self, name: str, runtime: str, model: str) -> ImageWorker:
        now = datetime.now(timezone.utc)
        worker = self.db.scalar(select(ImageWorker).where(ImageWorker.name == name))
        if worker:
            worker.runtime = runtime
            worker.model = model
            worker.status = "online"
            worker.last_seen_at = now
        else:
            worker = ImageWorker(
                name=name,
                runtime=runtime,
                model=model,
                status="online",
                last_seen_at=now,
            )
            self.db.add(worker)
        self.db.commit()
        self.db.refresh(worker)
        return worker

    def get(self, worker_id: UUID) -> ImageWorker | None:
        return self.db.get(ImageWorker, worker_id)

    def heartbeat(self, worker: ImageWorker) -> ImageWorker:
        worker.status = "online"
        worker.last_seen_at = datetime.now(timezone.utc)
        self.db.add(worker)
        self.db.commit()
        self.db.refresh(worker)
        return worker

    def claim_next_job(self, worker: ImageWorker) -> ImageGenerationJob | None:
        stmt = (
            select(ImageGenerationJob)
            .where(
                ImageGenerationJob.status == "pending",
                ImageGenerationJob.model == worker.model,
            )
            .order_by(ImageGenerationJob.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        job = self.db.scalar(stmt)
        if not job:
            self.db.rollback()
            return None
        job.status = "processing"
        job.worker_id = str(worker.id)
        worker.last_seen_at = datetime.now(timezone.utc)
        self.db.add_all([job, worker])
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_claimed_job(
        self,
        job_id: UUID,
        worker_id: UUID,
    ) -> ImageGenerationJob | None:
        stmt = select(ImageGenerationJob).where(
            ImageGenerationJob.id == job_id,
            ImageGenerationJob.worker_id == str(worker_id),
            ImageGenerationJob.status == "processing",
        )
        return self.db.scalar(stmt)

    def complete_job(
        self,
        job: ImageGenerationJob,
        asset: Asset,
    ) -> ImageGenerationJob:
        self.db.add(asset)
        self.db.flush()
        job.asset_id = asset.id
        job.status = "generated"
        job.error = None
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def fail_job(self, job: ImageGenerationJob, error: str) -> ImageGenerationJob:
        job.status = "failed"
        job.error = error
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job
