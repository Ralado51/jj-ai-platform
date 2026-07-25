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
                detail="A project with this slug already exists.",
            )
        try:
            return self.repository.create(data)
        except IntegrityError as exc:
            self.repository.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Project could not be created because a unique value already exists.",
            ) from exc

    def list(self, *, offset: int = 0, limit: int = 100) -> list[Project]:
        return self.repository.list(offset=offset, limit=limit)

    def get(self, project_id: UUID) -> Project:
        project = self.repository.get_by_id(project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found.",
            )
        return project

    def update(self, project_id: UUID, data: ProjectUpdate) -> Project:
        project = self.get(project_id)
        if data.slug is not None:
            existing = self.repository.get_by_slug(data.slug)
            if existing is not None and existing.id != project_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A project with this slug already exists.",
                )
        try:
            return self.repository.update(project, data)
        except IntegrityError as exc:
            self.repository.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Project could not be updated because a unique value already exists.",
            ) from exc

    def delete(self, project_id: UUID) -> None:
        project = self.get(project_id)
        self.repository.delete(project)
