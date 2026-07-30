from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=180)


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    is_favorite: bool | None = None


class ConversationMessageCreate(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=50000)
    model: str | None = Field(default=None, max_length=120)


class ConversationMessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    model: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: UUID
    project_id: UUID
    user_id: UUID
    title: str
    is_favorite: bool
    created_at: datetime
    updated_at: datetime
    messages: list[ConversationMessageResponse] = []

    model_config = {"from_attributes": True}


class ConversationListItem(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    is_favorite: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    total: int
    offset: int = 0
    limit: int = 50
    items: list[ConversationListItem]
