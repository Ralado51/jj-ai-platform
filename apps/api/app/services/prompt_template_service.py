from uuid import UUID

from fastapi import HTTPException, status

from app.models.prompt_template import PromptTemplate
from app.models.user import User, UserRole
from app.repositories.prompt_template_repository import PromptTemplateRepository
from app.schemas.prompt_template import PromptTemplateCreate, PromptTemplateUpdate


class PromptTemplateService:
    def __init__(self, repository: PromptTemplateRepository) -> None:
        self.repository = repository

    def create(self, data: PromptTemplateCreate, user: User) -> PromptTemplate:
        if data.is_public and user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Somente administradores podem criar templates públicos.",
            )
        return self.repository.create(data, owner_id=user.id)

    def list(
        self,
        *,
        user: User,
        project_id: UUID | None = None,
        category: str | None = None,
        favorite: bool | None = None,
        search: str | None = None,
        include_inactive: bool = False,
        offset: int = 0,
        limit: int = 100,
    ) -> list[PromptTemplate]:
        return self.repository.list(
            user_id=user.id,
            project_id=project_id,
            category=category,
            favorite=favorite,
            search=search,
            include_inactive=include_inactive and user.role == UserRole.ADMIN,
            offset=offset,
            limit=limit,
        )

    def get(self, template_id: UUID, user: User) -> PromptTemplate:
        template = self.repository.get_by_id(template_id)
        if template is None or not self._can_read(template, user):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template não encontrado.")
        return template

    def update(self, template_id: UUID, data: PromptTemplateUpdate, user: User) -> PromptTemplate:
        template = self.get(template_id, user)
        if not self._can_manage(template, user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para editar este template.")
        if data.is_public is True and user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Somente administradores podem publicar templates.",
            )
        return self.repository.update(template, data)

    def archive(self, template_id: UUID, user: User) -> PromptTemplate:
        template = self.get(template_id, user)
        if not self._can_manage(template, user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para arquivar este template.")
        return self.repository.archive(template)

    @staticmethod
    def _can_read(template: PromptTemplate, user: User) -> bool:
        return template.is_public or template.owner_id == user.id or user.role == UserRole.ADMIN

    @staticmethod
    def _can_manage(template: PromptTemplate, user: User) -> bool:
        return template.owner_id == user.id or user.role == UserRole.ADMIN
