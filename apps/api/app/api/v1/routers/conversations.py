from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_roles
from app.db.dependencies import get_db
from app.models.user import User, UserRole
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.conversation import (
    ConversationCreate,
    ConversationListResponse,
    ConversationMessageCreate,
    ConversationResponse,
    ConversationUpdate,
)
from app.services.conversation_service import ConversationService

router = APIRouter(tags=["conversations"])


def get_service(db: Session = Depends(get_db)) -> ConversationService:
    return ConversationService(
        conversation_repository=ConversationRepository(db),
        project_repository=ProjectRepository(db),
    )


@router.post(
    "/projects/{project_id}/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    project_id: UUID,
    data: ConversationCreate,
    service: ConversationService = Depends(get_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> ConversationResponse:
    return service.create(project_id, user.id, data)


@router.get(
    "/projects/{project_id}/conversations",
    response_model=ConversationListResponse,
)
def list_conversations(
    project_id: UUID,
    service: ConversationService = Depends(get_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> ConversationListResponse:
    return service.list(project_id, user.id)


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: UUID,
    service: ConversationService = Depends(get_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> ConversationResponse:
    return service.get(conversation_id, user.id)


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: UUID,
    data: ConversationUpdate,
    service: ConversationService = Depends(get_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> ConversationResponse:
    return service.update(conversation_id, user.id, data)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_conversation_message(
    conversation_id: UUID,
    data: ConversationMessageCreate,
    service: ConversationService = Depends(get_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> ConversationResponse:
    return service.add_message(conversation_id, user.id, data)


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_conversation(
    conversation_id: UUID,
    service: ConversationService = Depends(get_service),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MEMBER, UserRole.VIEWER)),
) -> Response:
    service.delete(conversation_id, user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
