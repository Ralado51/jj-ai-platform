from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowStep(BaseModel):
    agent_id: str = Field(min_length=1, max_length=80)
    instruction: str | None = Field(default=None, min_length=2, max_length=4000)


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    project_id: UUID | None = None
    steps: list[WorkflowStep] = Field(min_length=1, max_length=6)
    default_instruction: str | None = Field(default=None, min_length=2, max_length=12000)
    session_key: str | None = Field(default=None, min_length=1, max_length=120)
    use_memory: bool = True


class WorkflowUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    project_id: UUID | None = None
    steps: list[WorkflowStep] | None = Field(default=None, min_length=1, max_length=6)
    default_instruction: str | None = Field(default=None, min_length=2, max_length=12000)
    session_key: str | None = Field(default=None, min_length=1, max_length=120)
    use_memory: bool | None = None
    is_active: bool | None = None


class WorkflowResponse(BaseModel):
    id: UUID
    user_id: UUID
    project_id: UUID | None
    name: str
    description: str | None
    steps: list[WorkflowStep]
    default_instruction: str | None
    session_key: str | None
    use_memory: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
