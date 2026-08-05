from __future__ import annotations

import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.dependencies import get_db
from app.models.resource_registry import ResourceRegistry
from app.models.user import User, UserRole
from app.repositories.resource_registry_repository import ResourceRegistryRepository
from app.schemas.resources import ResourceCreateRequest, ResourceListResponse, ResourceResponse, ResourceUpdateRequest

router = APIRouter(prefix="/resources", tags=["resources"])


def get_repository(db: Session = Depends(get_db)) -> ResourceRegistryRepository:
    return ResourceRegistryRepository(db)


def serialize(item: ResourceRegistry, *, is_favorite: bool = False) -> ResourceResponse:
    return ResourceResponse(
        id=item.id,
        owner_id=item.owner_id,
        project_id=item.project_id,
        resource_type=item.resource_type,
        resource_id=item.resource_id,
        name=item.name,
        description=item.description,
        status=item.status,
        metadata=item.resource_metadata or {},
        labels=item.labels or [],
        is_favorite=is_favorite,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.post("", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
def register_resource(
    payload: ResourceCreateRequest,
    repository: ResourceRegistryRepository = Depends(get_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> ResourceResponse:
    existing = repository.find_registered(
        owner_id=user.id,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Resource is already registered.")
    item = repository.create(
        owner_id=user.id,
        values={
            "resource_type": payload.resource_type,
            "resource_id": payload.resource_id,
            "project_id": payload.project_id,
            "name": payload.name.strip(),
            "description": payload.description,
            "status": payload.status,
            "resource_metadata": payload.metadata,
            "labels": sorted(set(label.strip() for label in payload.labels if label.strip())),
        },
    )
    return serialize(item)


@router.get("", response_model=ResourceListResponse)
def list_resources(
    q: str | None = None,
    resource_type: str | None = None,
    project_id: UUID | None = None,
    resource_status: str | None = Query(default=None, alias="status"),
    labels: list[str] | None = Query(default=None),
    favorites_only: bool = False,
    page: int = 1,
    page_size: int = 50,
    repository: ResourceRegistryRepository = Depends(get_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> ResourceListResponse:
    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, 100))
    items, total = repository.list(
        owner_id=user.id,
        query=q,
        resource_type=resource_type,
        project_id=project_id,
        status=resource_status,
        labels=labels,
        favorites_only=favorites_only,
        offset=(safe_page - 1) * safe_page_size,
        limit=safe_page_size,
    )
    favorite_ids = repository.favorite_ids(user_id=user.id, registry_ids=[item.id for item in items])
    return ResourceListResponse(
        items=[serialize(item, is_favorite=item.id in favorite_ids) for item in items],
        total=total,
        page=safe_page,
        page_size=safe_page_size,
    )


@router.get("/{registry_id}", response_model=ResourceResponse)
def get_resource(
    registry_id: UUID,
    repository: ResourceRegistryRepository = Depends(get_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> ResourceResponse:
    item = repository.get(owner_id=user.id, registry_id=registry_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found.")
    favorites = repository.favorite_ids(user_id=user.id, registry_ids=[item.id])
    return serialize(item, is_favorite=item.id in favorites)


@router.patch("/{registry_id}", response_model=ResourceResponse)
def update_resource(
    registry_id: UUID,
    payload: ResourceUpdateRequest,
    repository: ResourceRegistryRepository = Depends(get_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> ResourceResponse:
    item = repository.get(owner_id=user.id, registry_id=registry_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found.")
    values = payload.model_dump(exclude_unset=True)
    if "metadata" in values:
        values["resource_metadata"] = values.pop("metadata")
    if "labels" in values and values["labels"] is not None:
        values["labels"] = sorted(set(label.strip() for label in values["labels"] if label.strip()))
    if "name" in values and values["name"] is not None:
        values["name"] = values["name"].strip()
    updated = repository.update(item=item, values=values)
    favorites = repository.favorite_ids(user_id=user.id, registry_ids=[updated.id])
    return serialize(updated, is_favorite=updated.id in favorites)


@router.put("/{registry_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
def favorite_resource(
    registry_id: UUID,
    repository: ResourceRegistryRepository = Depends(get_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> Response:
    if repository.get(owner_id=user.id, registry_id=registry_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found.")
    repository.set_favorite(user_id=user.id, registry_id=registry_id, enabled=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{registry_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
def unfavorite_resource(
    registry_id: UUID,
    repository: ResourceRegistryRepository = Depends(get_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> Response:
    if repository.get(owner_id=user.id, registry_id=registry_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found.")
    repository.set_favorite(user_id=user.id, registry_id=registry_id, enabled=False)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{registry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(
    registry_id: UUID,
    repository: ResourceRegistryRepository = Depends(get_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> Response:
    item = repository.get(owner_id=user.id, registry_id=registry_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found.")
    repository.delete(item=item)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
