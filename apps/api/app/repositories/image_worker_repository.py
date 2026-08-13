from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, lazyload

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
            worker = ImageWorker(name=name, runtime=runtime, model=model, status="online", last_seen_at=now)
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

    def claim_next_job(self, worker: ImageWorker, runtime_priority: tuple[str, ...] = (), online_timeout_seconds: int = 90, max_active_jobs: int = 1) -> ImageGenerationJob | None:
        if not self._worker_can_claim(worker, runtime_priority, online_timeout_seconds, max_active_jobs):
            self.db.rollback()
            return None
        stmt = (select(ImageGenerationJob).options(lazyload(ImageGenerationJob.asset)).where(ImageGenerationJob.status == "pending", ImageGenerationJob.model == worker.model).order_by(ImageGenerationJob.created_at.asc()).with_for_update(skip_locked=True, of=ImageGenerationJob).limit(1))
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

    def _worker_can_claim(self, worker: ImageWorker, runtime_priority: tuple[str, ...], online_timeout_seconds: int, max_active_jobs: int) -> bool:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=max(1, online_timeout_seconds))
        workers = list(self.db.scalars(select(ImageWorker).where(ImageWorker.model == worker.model, ImageWorker.status == "online", ImageWorker.last_seen_at >= cutoff)).all())
        if not workers:
            return False
        worker_ids = [str(item.id) for item in workers]
        active_rows = self.db.execute(select(ImageGenerationJob.worker_id, func.count(ImageGenerationJob.id)).where(ImageGenerationJob.status == "processing", ImageGenerationJob.worker_id.in_(worker_ids)).group_by(ImageGenerationJob.worker_id)).all()
        active_by_worker = {str(worker_id): int(count) for worker_id, count in active_rows}
        capacity = max(1, max_active_jobs)
        available = [item for item in workers if active_by_worker.get(str(item.id), 0) < capacity]
        if not available:
            return False
        priorities = {runtime.strip().lower(): index for index, runtime in enumerate(runtime_priority)}
        fallback_priority = len(priorities) + 100
        def routing_key(item: ImageWorker) -> tuple[int, int, str]:
            return priorities.get(item.runtime.strip().lower(), fallback_priority), active_by_worker.get(str(item.id), 0), item.name
        selected = min(available, key=routing_key)
        return selected.id == worker.id

    def get_claimed_job(self, job_id: UUID, worker_id: UUID) -> ImageGenerationJob | None:
        stmt = select(ImageGenerationJob).where(ImageGenerationJob.id == job_id, ImageGenerationJob.worker_id == str(worker_id), ImageGenerationJob.status == "processing")
        return self.db.scalar(stmt)

    def complete_job(self, job: ImageGenerationJob, asset: Asset) -> ImageGenerationJob:
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
