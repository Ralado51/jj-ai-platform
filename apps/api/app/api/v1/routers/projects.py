from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


def get_service(db: Session = Depends(get_db)) -> ProjectService:
    return ProjectService(ProjectRepository(db))


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    service: ProjectService = Depends(get_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> ProjectResponse:
    return service.create(payload, owner_id=user.id)


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    is_active: bool | None = Query(default=True),
    search: str | None = Query(default=None, min_length=1, max_length=150),
    service: ProjectService = Depends(get_service),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> list[ProjectResponse]:
    return service.list(offset=offset, limit=limit, is_active=is_active, search=search)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID,
    service: ProjectService = Depends(get_service),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> ProjectResponse:
    return service.get(project_id)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    service: ProjectService = Depends(get_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER)),
) -> ProjectResponse:
    return service.update(project_id, payload, owner_id=user.id)


@router.delete("/{project_id}", response_model=ProjectResponse)
def archive_project(
    project_id: UUID,
    service: ProjectService = Depends(get_service),
    user: User = Depends(require_roles(UserRole.ADMIN)),
) -> ProjectResponse:
    return service.archive(project_id, owner_id=user.id)
