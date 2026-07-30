from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PromptTemplateBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    category: str = Field(default="general", min_length=1, max_length=80)
    content: str = Field(min_length=1)
    variables: list[str] = Field(default_factory=list)
    is_public: bool = False
    is_favorite: bool = False
    is_active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("variables")
    @classmethod
    def normalize_variables(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            item = value.strip()
            if item and item not in normalized:
                normalized.append(item)
        return normalized


class PromptTemplateCreate(PromptTemplateBase):
    project_id: UUID | None = None


class PromptTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    category: str | None = Field(default=None, min_length=1, max_length=80)
    content: str | None = Field(default=None, min_length=1)
    variables: list[str] | None = None
    is_public: bool | None = None
    is_favorite: bool | None = None
    is_active: bool | None = None
    metadata: dict[str, Any] | None = None


class PromptTemplateResponse(PromptTemplateBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    project_id: UUID | None
    owner_id: UUID | None
    created_at: datetime
    updated_at: datetime

    @property
    def metadata(self) -> dict[str, Any]:
        return self.metadata_
