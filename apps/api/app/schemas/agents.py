from __future__ import annotations

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


class AgentRunResponse(BaseModel):
    agent: AgentDescriptorResponse
    routing_reason: str
    content: str
    provider: str
    model: str
