from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.models.project import Project
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    def __init__(self, repository: ProjectRepository) -> None:
        self.repository = repository

    def create(self, data: ProjectCreate) -> Project:
        if self.repository.get_by_slug(data.slug):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe um projeto com este slug.",
            )
        try:
            return self.repository.create(data)
        except IntegrityError as exc:
            self.repository.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Não foi possível criar o projeto porque um valor único já existe.",
            ) from exc

    def list(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        is_active: bool | None = True,
        search: str | None = None,
    ) -> list[Project]:
        return self.repository.list(
            offset=offset,
            limit=limit,
            is_active=is_active,
            search=search,
        )

    def get(self, project_id: UUID) -> Project:
        project = self.repository.get_by_id(project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Projeto não encontrado.",
            )
        return project

    def update(self, project_id: UUID, data: ProjectUpdate) -> Project:
        project = self.get(project_id)
        if data.slug is not None:
            existing = self.repository.get_by_slug(data.slug)
            if existing is not None and existing.id != project_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Já existe um projeto com este slug.",
                )
        try:
            return self.repository.update(project, data)
        except IntegrityError as exc:
            self.repository.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Não foi possível atualizar o projeto porque um valor único já existe.",
            ) from exc

    def archive(self, project_id: UUID) -> Project:
        project = self.get(project_id)
        if not project.is_active:
            return project
        return self.repository.archive(project)
