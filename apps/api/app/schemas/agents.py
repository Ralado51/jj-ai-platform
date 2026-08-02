from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.services.model_router import AITaskType


class AgentDescriptorResponse(BaseModel):
    id: str
    name: str
    description: str
    task: AITaskType


class AgentRunRequest(BaseModel):
    instruction: str = Field(min_length=2, max_length=12000)
    agent_id: str | None = Field(default=None, min_length=1, max_length=80)
    project_id: UUID | None = None
    session_key: str | None = Field(default=None, min_length=1, max_length=120)
    use_memory: bool = True


class AgentRunResponse(BaseModel):
    execution_id: UUID | None = None
    agent: AgentDescriptorResponse
    routing_reason: str
    content: str
    provider: str
    model: str
    model_selection_source: str = "configured_router"
    duration_ms: int = 0
    memory_items_used: int = 0
    session_key: str | None = None
    project_id: UUID | None = None


class AgentExecutionResponse(BaseModel):
    id: UUID
    agent_id: str
    task_type: str
    session_key: str | None
    instruction: str
    response: str
    routing_reason: str
    provider: str
    model: str
    duration_ms: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentMemoryResponse(BaseModel):
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
