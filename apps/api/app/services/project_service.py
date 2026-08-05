from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.events.bus import DomainEventBus, domain_event_bus
from app.events.resource_events import ResourceUpserted
from app.models.project import Project
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    def __init__(self, repository: ProjectRepository, event_bus: DomainEventBus | None = None) -> None:
        self.repository = repository
        self.event_bus = event_bus or domain_event_bus

    def _publish(self, project: Project, *, owner_id: UUID | None) -> None:
        if owner_id is None:
            return
        self.event_bus.publish(ResourceUpserted(
            owner_id=owner_id,
            resource_type="project",
            resource_id=project.id,
            project_id=project.id,
            name=project.name,
            description=getattr(project, "description", None),
            status="active" if project.is_active else "archived",
            metadata={"slug": project.slug},
        ))

    def create(self, data: ProjectCreate, *, owner_id: UUID | None = None) -> Project:
        if self.repository.get_by_slug(data.slug):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe um projeto com este slug.")
        try:
            project = self.repository.create(data)
            self._publish(project, owner_id=owner_id)
            return project
        except IntegrityError as exc:
            self.repository.db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Não foi possível criar o projeto porque um valor único já existe.") from exc

    def list(self, *, offset: int = 0, limit: int = 100, is_active: bool | None = True, search: str | None = None) -> list[Project]:
        return self.repository.list(offset=offset, limit=limit, is_active=is_active, search=search)

    def get(self, project_id: UUID) -> Project:
        project = self.repository.get_by_id(project_id)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado.")
        return project

    def update(self, project_id: UUID, data: ProjectUpdate, *, owner_id: UUID | None = None) -> Project:
        project = self.get(project_id)
        if data.slug is not None:
            existing = self.repository.get_by_slug(data.slug)
            if existing is not None and existing.id != project_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe um projeto com este slug.")
        try:
            project = self.repository.update(project, data)
            self._publish(project, owner_id=owner_id)
            return project
        except IntegrityError as exc:
            self.repository.db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Não foi possível atualizar o projeto porque um valor único já existe.") from exc

    def archive(self, project_id: UUID, *, owner_id: UUID | None = None) -> Project:
        project = self.get(project_id)
        if project.is_active:
            project = self.repository.archive(project)
        self._publish(project, owner_id=owner_id)
        return project
