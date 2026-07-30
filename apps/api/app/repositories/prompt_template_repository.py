from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.prompt_template import PromptTemplate
from app.schemas.prompt_template import PromptTemplateCreate, PromptTemplateUpdate


class PromptTemplateRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: PromptTemplateCreate, owner_id: UUID) -> PromptTemplate:
        values = data.model_dump()
        values["owner_id"] = owner_id
        values["metadata_"] = values.pop("metadata")
        template = PromptTemplate(**values)
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template

    def list(
        self,
        *,
        user_id: UUID,
        project_id: UUID | None = None,
        category: str | None = None,
        favorite: bool | None = None,
        search: str | None = None,
        include_inactive: bool = False,
        offset: int = 0,
        limit: int = 100,
    ) -> list[PromptTemplate]:
        statement = select(PromptTemplate).where(
            or_(PromptTemplate.owner_id == user_id, PromptTemplate.is_public.is_(True))
        )
        if project_id is not None:
            statement = statement.where(
                or_(PromptTemplate.project_id == project_id, PromptTemplate.project_id.is_(None))
            )
        if category:
            statement = statement.where(PromptTemplate.category == category)
        if favorite is not None:
            statement = statement.where(PromptTemplate.is_favorite == favorite)
        if search:
            term = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    PromptTemplate.name.ilike(term),
                    PromptTemplate.description.ilike(term),
                    PromptTemplate.content.ilike(term),
                )
            )
        if not include_inactive:
            statement = statement.where(PromptTemplate.is_active.is_(True))
        statement = statement.order_by(
            PromptTemplate.is_favorite.desc(),
            PromptTemplate.updated_at.desc(),
        ).offset(offset).limit(limit)
        return list(self.db.scalars(statement).all())

    def get_by_id(self, template_id: UUID) -> PromptTemplate | None:
        return self.db.get(PromptTemplate, template_id)

    def update(self, template: PromptTemplate, data: PromptTemplateUpdate) -> PromptTemplate:
        values = data.model_dump(exclude_unset=True)
        if "metadata" in values:
            values["metadata_"] = values.pop("metadata")
        for field, value in values.items():
            setattr(template, field, value)
        self.db.commit()
        self.db.refresh(template)
        return template

    def archive(self, template: PromptTemplate) -> PromptTemplate:
        template.is_active = False
        self.db.commit()
        self.db.refresh(template)
        return template
