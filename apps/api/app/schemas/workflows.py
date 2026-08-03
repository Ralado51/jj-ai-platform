from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.agents import AgentRunResponse


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


class WorkflowRunRequest(BaseModel):
    instruction: str | None = Field(default=None, min_length=2, max_length=12000)
    project_id: UUID | None = None
    session_key: str | None = Field(default=None, min_length=1, max_length=120)
    use_memory: bool | None = None


class WorkflowRetryFromStepRequest(WorkflowRunRequest):
    step: int = Field(ge=1, le=6)


class WorkflowRunResponse(BaseModel):
    execution_id: UUID
    workflow_id: UUID
    workflow_name: str
    steps: list[AgentRunResponse]
    final_content: str
    total_duration_ms: int
    project_id: UUID | None = None
    session_key: str | None = None
    use_memory: bool


class WorkflowExecutionStepResponse(BaseModel):
    index: int
    agent_id: str
    agent_name: str
    task: str
    status: str = "completed"
    execution_id: UUID | None = None
    provider: str
    model: str
    model_selection_source: str
    routing_reason: str
    duration_ms: int
    memory_items_used: int
    content: str


class WorkflowExecutionResponse(BaseModel):
    id: UUID
    workflow_id: UUID
    project_id: UUID | None
    parent_execution_id: UUID | None = None
    retry_from_step: int | None = None
    workflow_name: str
    status: str
    instruction: str
    session_key: str | None
    use_memory: bool
    steps_total: int
    steps_completed: int
    total_duration_ms: int
    final_content: str | None
    error_message: str | None
    step_details: list[WorkflowExecutionStepResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


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
