from uuid import UUID

from fastapi import HTTPException, status

from app.events.bus import DomainEventBus, domain_event_bus
from app.events.types import PromptArchived, PromptCreated, PromptUpdated
from app.models.prompt_template import PromptTemplate
from app.models.user import User, UserRole
from app.repositories.prompt_template_repository import PromptTemplateRepository
from app.schemas.prompt_template import PromptTemplateCreate, PromptTemplateUpdate


class PromptTemplateService:
    def __init__(
        self,
        repository: PromptTemplateRepository,
        event_bus: DomainEventBus = domain_event_bus,
    ) -> None:
        self.repository = repository
        self.event_bus = event_bus

    def create(self, data: PromptTemplateCreate, user: User) -> PromptTemplate:
        if data.is_public and user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Somente administradores podem criar templates públicos.",
            )
        template = self.repository.create(data, owner_id=user.id)
        self.event_bus.publish(
            PromptCreated(
                actor_id=user.id,
                owner_id=user.id,
                project_id=template.project_id,
                prompt_id=template.id,
                current_values=self._snapshot(template),
            )
        )
        return template

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
        previous_values = self._snapshot(template)
        template = self.repository.update(template, data)
        self.event_bus.publish(
            PromptUpdated(
                actor_id=user.id,
                owner_id=template.owner_id or user.id,
                project_id=template.project_id,
                prompt_id=template.id,
                previous_values=previous_values,
                current_values=self._snapshot(template),
            )
        )
        return template

    def archive(self, template_id: UUID, user: User) -> PromptTemplate:
        template = self.get(template_id, user)
        if not self._can_manage(template, user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para arquivar este template.")
        template = self.repository.archive(template)
        self.event_bus.publish(
            PromptArchived(
                actor_id=user.id,
                owner_id=template.owner_id or user.id,
                project_id=template.project_id,
                prompt_id=template.id,
                current_values=self._snapshot(template),
            )
        )
        return template

    def restore(self, template_id: UUID, snapshot: dict, user: User) -> PromptTemplate:
        allowed_fields = {
            "name",
            "description",
            "category",
            "content",
            "variables",
            "is_public",
            "is_favorite",
            "is_active",
            "metadata",
        }
        payload = PromptTemplateUpdate(**{key: value for key, value in snapshot.items() if key in allowed_fields})
        return self.update(template_id, payload, user)

    @staticmethod
    def _snapshot(template: PromptTemplate) -> dict:
        return {
            "name": template.name,
            "description": template.description,
            "category": template.category,
            "content": template.content,
            "variables": list(template.variables),
            "is_public": template.is_public,
            "is_favorite": template.is_favorite,
            "is_active": template.is_active,
            "metadata": dict(template.metadata_),
        }

    @staticmethod
    def _can_read(template: PromptTemplate, user: User) -> bool:
        return template.is_public or template.owner_id == user.id or user.role == UserRole.ADMIN

    @staticmethod
    def _can_manage(template: PromptTemplate, user: User) -> bool:
        return template.owner_id == user.id or user.role == UserRole.ADMIN
