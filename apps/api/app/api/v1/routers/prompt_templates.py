from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.prompt_template_repository import PromptTemplateRepository
from app.repositories.resource_version_repository import ResourceVersionRepository
from app.schemas.prompt_template import (
    PromptTemplateCreate,
    PromptTemplateResponse,
    PromptTemplateUpdate,
)
from app.services.prompt_template_service import PromptTemplateService

router = APIRouter(prefix="/prompt-templates", tags=["prompt-templates"])


def get_service(db: Session = Depends(get_db)) -> PromptTemplateService:
    return PromptTemplateService(PromptTemplateRepository(db))


def get_version_repository(db: Session = Depends(get_db)) -> ResourceVersionRepository:
    return ResourceVersionRepository(db)


@router.post("", response_model=PromptTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_prompt_template(
    payload: PromptTemplateCreate,
    service: PromptTemplateService = Depends(get_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> PromptTemplateResponse:
    return service.create(payload, user)


@router.get("", response_model=list[PromptTemplateResponse])
def list_prompt_templates(
    project_id: UUID | None = Query(default=None),
    category: str | None = Query(default=None, min_length=1, max_length=80),
    favorite: bool | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1, max_length=150),
    include_inactive: bool = Query(default=False),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    service: PromptTemplateService = Depends(get_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> list[PromptTemplateResponse]:
    return service.list(
        user=user,
        project_id=project_id,
        category=category,
        favorite=favorite,
        search=search,
        include_inactive=include_inactive,
        offset=offset,
        limit=limit,
    )


@router.get("/{template_id}", response_model=PromptTemplateResponse)
def get_prompt_template(
    template_id: UUID,
    service: PromptTemplateService = Depends(get_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> PromptTemplateResponse:
    return service.get(template_id, user)


@router.patch("/{template_id}", response_model=PromptTemplateResponse)
def update_prompt_template(
    template_id: UUID,
    payload: PromptTemplateUpdate,
    service: PromptTemplateService = Depends(get_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> PromptTemplateResponse:
    return service.update(template_id, payload, user)


@router.delete("/{template_id}", response_model=PromptTemplateResponse)
def archive_prompt_template(
    template_id: UUID,
    service: PromptTemplateService = Depends(get_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> PromptTemplateResponse:
    return service.archive(template_id, user)


@router.post("/{template_id}/versions/{version_number}/restore", response_model=PromptTemplateResponse)
def restore_prompt_template_version(
    template_id: UUID,
    version_number: int,
    service: PromptTemplateService = Depends(get_service),
    version_repository: ResourceVersionRepository = Depends(get_version_repository),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> PromptTemplateResponse:
    template = service.get(template_id, user)
    owner_id = template.owner_id or user.id
    version = version_repository.get(
        owner_id=owner_id,
        resource_type="prompt",
        resource_id=template_id,
        version_number=version_number,
    )
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt version not found.")
    return service.restore(template_id, version.snapshot, user)
