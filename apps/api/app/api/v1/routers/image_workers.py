from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.core.config import Settings, get_settings
from app.db.dependencies import get_db
from app.models.image_generation_job import ImageGenerationJob
from app.models.image_worker import ImageWorker
from app.models.user import User, UserRole
from app.repositories.image_worker_repository import ImageWorkerRepository
from app.schemas.image_jobs import ImageJobResponse
from app.schemas.image_workers import (
    ImageWorkerClaimRequest,
    ImageWorkerClaimResponse,
    ImageWorkerFailedRequest,
    ImageWorkerHeartbeatRequest,
    ImageWorkerManagementResponse,
    ImageWorkerManagementSummary,
    ImageWorkerRegisterRequest,
    ImageWorkerResponse,
    ImageWorkerResultRequest,
)
from app.services.image_worker_service import ImageWorkerService

router = APIRouter(prefix="/image-workers", tags=["image-workers"])


def require_worker_token(
    x_jj_worker_token: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    expected = settings.image_worker_token
    if not expected or not x_jj_worker_token or not secrets.compare_digest(expected, x_jj_worker_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid image worker token.")


def get_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ImageWorkerService:
    return ImageWorkerService(ImageWorkerRepository(db), settings)


@router.get("", response_model=ImageWorkerManagementSummary)
def list_workers(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> ImageWorkerManagementSummary:
    workers = list(db.scalars(select(ImageWorker).order_by(ImageWorker.last_seen_at.desc())).all())
    online_cutoff = datetime.now(timezone.utc) - timedelta(seconds=90)
    items: list[ImageWorkerManagementResponse] = []

    for worker in workers:
        key = str(worker.id)

        def count(statuses: tuple[str, ...]) -> int:
            value = db.scalar(
                select(func.count()).select_from(ImageGenerationJob).where(
                    ImageGenerationJob.worker_id == key,
                    ImageGenerationJob.status.in_(statuses),
                )
            )
            return int(value or 0)

        is_online = worker.last_seen_at >= online_cutoff
        items.append(
            ImageWorkerManagementResponse(
                id=worker.id,
                name=worker.name,
                runtime=worker.runtime,
                model=worker.model,
                status=worker.status,
                effective_status="online" if is_online else "offline",
                is_online=is_online,
                active_jobs=count(("processing",)),
                completed_jobs=count(("generated", "approved", "rejected")),
                failed_jobs=count(("failed",)),
                last_seen_at=worker.last_seen_at,
                created_at=worker.created_at,
                updated_at=worker.updated_at,
            )
        )

    return ImageWorkerManagementSummary(
        total_workers=len(items),
        online_workers=sum(1 for item in items if item.is_online),
        offline_workers=sum(1 for item in items if not item.is_online),
        active_jobs=sum(item.active_jobs for item in items),
        completed_jobs=sum(item.completed_jobs for item in items),
        failed_jobs=sum(item.failed_jobs for item in items),
        workers=items,
    )


@router.post("/register", response_model=ImageWorkerResponse, dependencies=[Depends(require_worker_token)])
def register_worker(payload: ImageWorkerRegisterRequest, service: ImageWorkerService = Depends(get_service)) -> ImageWorkerResponse:
    return service.register(payload)


@router.post("/heartbeat", response_model=ImageWorkerResponse, dependencies=[Depends(require_worker_token)])
def heartbeat(payload: ImageWorkerHeartbeatRequest, service: ImageWorkerService = Depends(get_service)) -> ImageWorkerResponse:
    return service.heartbeat(payload.worker_id)


@router.post("/next-job", response_model=ImageWorkerClaimResponse, dependencies=[Depends(require_worker_token)])
def next_job(payload: ImageWorkerClaimRequest, service: ImageWorkerService = Depends(get_service)) -> ImageWorkerClaimResponse:
    job = service.claim_next_job(payload.worker_id)
    if not job:
        return ImageWorkerClaimResponse()
    return ImageWorkerClaimResponse(
        job_id=job.id,
        project_id=job.project_id,
        external_id=job.external_id,
        provider=job.provider,
        model=job.model,
        prompt=job.prompt,
        width=job.width,
        height=job.height,
        seed=job.seed,
    )


@router.post("/jobs/{job_id}/result", response_model=ImageJobResponse, dependencies=[Depends(require_worker_token)])
def submit_result(
    job_id: UUID,
    payload: ImageWorkerResultRequest,
    service: ImageWorkerService = Depends(get_service),
) -> ImageJobResponse:
    return service.complete_job(
        job_id=job_id,
        worker_id=payload.worker_id,
        image_base64=payload.image_base64,
        mime_type=payload.mime_type,
        seed=payload.seed,
    )


@router.post("/jobs/{job_id}/failed", response_model=ImageJobResponse, dependencies=[Depends(require_worker_token)])
def submit_failure(
    job_id: UUID,
    payload: ImageWorkerFailedRequest,
    service: ImageWorkerService = Depends(get_service),
) -> ImageJobResponse:
    return service.fail_job(job_id, payload.worker_id, payload.error)
