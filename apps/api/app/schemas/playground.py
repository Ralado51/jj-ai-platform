from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PlaygroundSessionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    project_id: UUID | None = None


class PlaygroundSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    project_id: UUID | None
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PlaygroundStep(BaseModel):
    agent_id: str = Field(min_length=1, max_length=80)
    instruction: str | None = Field(default=None, max_length=4000)


class PlaygroundRunCreate(BaseModel):
    mode: Literal["agent", "orchestration"] = "agent"
    input: str = Field(min_length=2, max_length=12000)
    agent_id: str | None = Field(default=None, max_length=80)
    steps: list[PlaygroundStep] = Field(default_factory=list, max_length=6)

    @model_validator(mode="after")
    def validate_mode(self):
        if self.mode == "agent" and self.steps:
            raise ValueError("steps are only supported in orchestration mode")
        if self.mode == "orchestration" and not self.steps:
            raise ValueError("orchestration mode requires at least one step")
        return self


class PlaygroundRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    owner_id: UUID
    mode: str
    status: str
    input: str
    output: str
    steps: list[dict]
    provider: str | None
    model: str | None
    duration_ms: int
    error: str | None
    created_at: datetime
    updated_at: datetime
