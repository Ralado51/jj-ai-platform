from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.conversation import Conversation, ConversationMessage


class ConversationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, project_id: UUID, user_id: UUID, title: str) -> Conversation:
        conversation = Conversation(project_id=project_id, user_id=user_id, title=title)
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def list_for_project(self, *, project_id: UUID, user_id: UUID) -> list[Conversation]:
        statement = (
            select(Conversation)
            .where(
                Conversation.project_id == project_id,
                Conversation.user_id == user_id,
            )
            .order_by(Conversation.is_favorite.desc(), Conversation.updated_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def count_for_project(self, *, project_id: UUID, user_id: UUID) -> int:
        statement = select(func.count(Conversation.id)).where(
            Conversation.project_id == project_id,
            Conversation.user_id == user_id,
        )
        return int(self.db.scalar(statement) or 0)

    def get(self, *, conversation_id: UUID, user_id: UUID) -> Conversation | None:
        statement = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        return self.db.scalar(statement)

    def update(self, conversation: Conversation, *, title: str | None, is_favorite: bool | None) -> Conversation:
        if title is not None:
            conversation.title = title
        if is_favorite is not None:
            conversation.is_favorite = is_favorite
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def delete(self, conversation: Conversation) -> None:
        self.db.delete(conversation)
        self.db.commit()

    def add_message(
        self,
        *,
        conversation: Conversation,
        role: str,
        content: str,
        model: str | None,
    ) -> ConversationMessage:
        message = ConversationMessage(
            conversation_id=conversation.id,
            role=role,
            content=content,
            model=model,
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        self.db.refresh(conversation)
        return message
