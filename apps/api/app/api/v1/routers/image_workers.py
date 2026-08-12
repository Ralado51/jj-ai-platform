from __future__ import annotations

import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.dependencies import get_db
from app.repositories.image_worker_repository import ImageWorkerRepository
from app.schemas.image_jobs import ImageJobResponse
from app.schemas.image_workers import (
    ImageWorkerClaimRequest,
    ImageWorkerClaimResponse,
    ImageWorkerFailedRequest,
    ImageWorkerHeartbeatRequest,
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
    if not expected or not x_jj_worker_token or not secrets.compare_digest(
        expected,
        x_jj_worker_token,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid image worker token.",
        )


def get_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ImageWorkerService:
    return ImageWorkerService(ImageWorkerRepository(db), settings)


@router.post(
    "/register",
    response_model=ImageWorkerResponse,
    dependencies=[Depends(require_worker_token)],
)
def register_worker(
    payload: ImageWorkerRegisterRequest,
    service: ImageWorkerService = Depends(get_service),
) -> ImageWorkerResponse:
    return service.register(payload)


@router.post(
    "/heartbeat",
    response_model=ImageWorkerResponse,
    dependencies=[Depends(require_worker_token)],
)
def heartbeat(
    payload: ImageWorkerHeartbeatRequest,
    service: ImageWorkerService = Depends(get_service),
) -> ImageWorkerResponse:
    return service.heartbeat(payload.worker_id)


@router.post(
    "/next-job",
    response_model=ImageWorkerClaimResponse,
    dependencies=[Depends(require_worker_token)],
)
def next_job(
    payload: ImageWorkerClaimRequest,
    service: ImageWorkerService = Depends(get_service),
) -> ImageWorkerClaimResponse:
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


@router.post(
    "/jobs/{job_id}/result",
    response_model=ImageJobResponse,
    dependencies=[Depends(require_worker_token)],
)
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


@router.post(
    "/jobs/{job_id}/failed",
    response_model=ImageJobResponse,
    dependencies=[Depends(require_worker_token)],
)
def submit_failure(
    job_id: UUID,
    payload: ImageWorkerFailedRequest,
    service: ImageWorkerService = Depends(get_service),
) -> ImageJobResponse:
    return service.fail_job(job_id, payload.worker_id, payload.error)
