from uuid import UUID

from fastapi import HTTPException, status

from app.repositories.conversation_repository import ConversationRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.conversation import (
    ConversationCreate,
    ConversationListResponse,
    ConversationMessageCreate,
    ConversationResponse,
    ConversationUpdate,
)


class ConversationService:
    def __init__(
        self,
        *,
        conversation_repository: ConversationRepository,
        project_repository: ProjectRepository,
    ) -> None:
        self.conversation_repository = conversation_repository
        self.project_repository = project_repository

    def create(self, project_id: UUID, user_id: UUID, data: ConversationCreate) -> ConversationResponse:
        self._ensure_project(project_id)
        title = (data.title or "Nova conversa").strip() or "Nova conversa"
        conversation = self.conversation_repository.create(
            project_id=project_id,
            user_id=user_id,
            title=title,
        )
        return ConversationResponse.model_validate(conversation)

    def list(self, project_id: UUID, user_id: UUID) -> ConversationListResponse:
        self._ensure_project(project_id)
        items = self.conversation_repository.list_for_project(
            project_id=project_id,
            user_id=user_id,
        )
        return ConversationListResponse(
            total=self.conversation_repository.count_for_project(
                project_id=project_id,
                user_id=user_id,
            ),
            items=items,
        )

    def get(self, conversation_id: UUID, user_id: UUID) -> ConversationResponse:
        conversation = self._get_owned(conversation_id, user_id)
        return ConversationResponse.model_validate(conversation)

    def update(
        self,
        conversation_id: UUID,
        user_id: UUID,
        data: ConversationUpdate,
    ) -> ConversationResponse:
        conversation = self._get_owned(conversation_id, user_id)
        title = data.title.strip() if data.title is not None else None
        conversation = self.conversation_repository.update(
            conversation,
            title=title,
            is_favorite=data.is_favorite,
        )
        return ConversationResponse.model_validate(conversation)

    def delete(self, conversation_id: UUID, user_id: UUID) -> None:
        conversation = self._get_owned(conversation_id, user_id)
        self.conversation_repository.delete(conversation)

    def add_message(
        self,
        conversation_id: UUID,
        user_id: UUID,
        data: ConversationMessageCreate,
    ) -> ConversationResponse:
        conversation = self._get_owned(conversation_id, user_id)
        self.conversation_repository.add_message(
            conversation=conversation,
            role=data.role,
            content=data.content.strip(),
            model=data.model,
        )
        conversation = self._get_owned(conversation_id, user_id)
        return ConversationResponse.model_validate(conversation)

    def _ensure_project(self, project_id: UUID) -> None:
        if self.project_repository.get_by_id(project_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado.")

    def _get_owned(self, conversation_id: UUID, user_id: UUID):
        conversation = self.conversation_repository.get(
            conversation_id=conversation_id,
            user_id=user_id,
        )
        if conversation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
        return conversation
