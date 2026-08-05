from __future__ import annotations

import datetime as dt
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ResourceType = Literal[
    "project", "workflow", "prompt", "agent", "model", "dataset", "knowledge_base", "budget", "execution"
]


class ResourceCreateRequest(BaseModel):
    resource_type: ResourceType
    resource_id: UUID
    project_id: UUID | None = None
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: str = Field(default="active", min_length=1, max_length=30)
    metadata: dict = Field(default_factory=dict)
    labels: list[str] = Field(default_factory=list, max_length=30)


class ResourceUpdateRequest(BaseModel):
    project_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: str | None = Field(default=None, min_length=1, max_length=30)
    metadata: dict | None = None
    labels: list[str] | None = Field(default=None, max_length=30)


class ResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    project_id: UUID | None
    resource_type: str
    resource_id: UUID
    name: str
    description: str | None
    status: str
    metadata: dict
    labels: list[str]
    is_favorite: bool = False
    created_at: dt.datetime
    updated_at: dt.datetime


class ResourceListResponse(BaseModel):
    items: list[ResourceResponse]
    total: int
    page: int
    page_size: int
