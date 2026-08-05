from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.resource_version_repository import ResourceVersionRepository
from app.schemas.resource_versions import ResourceVersionListResponse, ResourceVersionResponse

router = APIRouter(prefix="/resource-versions", tags=["versions"])


def get_repository(db: Session = Depends(get_db)) -> ResourceVersionRepository:
    return ResourceVersionRepository(db)


@router.get("", response_model=ResourceVersionListResponse)
def list_resource_versions(
    resource_type: str | None = None,
    resource_id: UUID | None = None,
    project_id: UUID | None = None,
    page: int = 1,
    page_size: int = 50,
    repository: ResourceVersionRepository = Depends(get_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> ResourceVersionListResponse:
    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, 100))
    items, total = repository.list(
        owner_id=user.id,
        resource_type=resource_type,
        resource_id=resource_id,
        project_id=project_id,
        offset=(safe_page - 1) * safe_page_size,
        limit=safe_page_size,
    )
    return ResourceVersionListResponse(
        items=[ResourceVersionResponse.model_validate(item) for item in items],
        total=total,
        page=safe_page,
        page_size=safe_page_size,
    )


@router.get("/{resource_type}/{resource_id}/{version_number}", response_model=ResourceVersionResponse)
def get_resource_version(
    resource_type: str,
    resource_id: UUID,
    version_number: int,
    repository: ResourceVersionRepository = Depends(get_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> ResourceVersionResponse:
    item = repository.get(
        owner_id=user.id,
        resource_type=resource_type,
        resource_id=resource_id,
        version_number=version_number,
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource version not found.")
    return ResourceVersionResponse.model_validate(item)
