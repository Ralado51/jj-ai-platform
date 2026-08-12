from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.image_generation_job_repository import ImageGenerationJobRepository
from app.schemas.image_jobs import (
    ImageJobBatchCreate,
    ImageJobBatchResponse,
    ImageJobCreate,
    ImageJobResponse,
    ImageJobReviewRequest,
)
from app.services.image_generation_job_service import ImageGenerationJobService

router = APIRouter(prefix="/images/jobs", tags=["image-jobs"])


def get_service(db: Session = Depends(get_db)) -> ImageGenerationJobService:
    return ImageGenerationJobService(ImageGenerationJobRepository(db))


@router.post("", response_model=ImageJobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: ImageJobCreate,
    service: ImageGenerationJobService = Depends(get_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> ImageJobResponse:
    return service.create(owner_id=user.id, payload=payload)


@router.post("/batch", response_model=ImageJobBatchResponse, status_code=status.HTTP_201_CREATED)
def create_batch(
    payload: ImageJobBatchCreate,
    service: ImageGenerationJobService = Depends(get_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> ImageJobBatchResponse:
    jobs = service.create_batch(owner_id=user.id, payload=payload)
    return ImageJobBatchResponse(total=len(jobs), jobs=jobs)


@router.get("", response_model=list[ImageJobResponse])
def list_jobs(
    job_status: str | None = Query(default=None, alias="status"),
    project_id: UUID | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    service: ImageGenerationJobService = Depends(get_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> list[ImageJobResponse]:
    return service.repository.list(
        owner_id=user.id,
        status=job_status,
        project_id=project_id,
        offset=offset,
        limit=limit,
    )


@router.get("/{job_id}", response_model=ImageJobResponse)
def get_job(
    job_id: UUID,
    service: ImageGenerationJobService = Depends(get_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> ImageJobResponse:
    return service.get(job_id=job_id, owner_id=user.id)


@router.post("/{job_id}/review", response_model=ImageJobResponse)
def review_job(
    job_id: UUID,
    payload: ImageJobReviewRequest,
    service: ImageGenerationJobService = Depends(get_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> ImageJobResponse:
    return service.review(job_id=job_id, owner_id=user.id, action=payload.action)
