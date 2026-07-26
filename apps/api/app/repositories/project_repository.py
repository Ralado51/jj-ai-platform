from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: ProjectCreate) -> Project:
        project = Project(**data.model_dump())
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def list(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        is_active: bool | None = True,
        search: str | None = None,
    ) -> list[Project]:
        statement = select(Project)

        if is_active is not None:
            statement = statement.where(Project.is_active == is_active)

        if search:
            term = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    Project.name.ilike(term),
                    Project.slug.ilike(term),
                    Project.description.ilike(term),
                )
            )

        statement = (
            statement.order_by(Project.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def get_by_id(self, project_id: UUID) -> Project | None:
        return self.db.get(Project, project_id)

    def get_by_slug(self, slug: str) -> Project | None:
        statement = select(Project).where(Project.slug == slug)
        return self.db.scalar(statement)

    def update(self, project: Project, data: ProjectUpdate) -> Project:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(project, field, value)
        self.db.commit()
        self.db.refresh(project)
        return project

    def archive(self, project: Project) -> Project:
        project.is_active = False
        self.db.commit()
        self.db.refresh(project)
        return project
