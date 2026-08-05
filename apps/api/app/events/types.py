from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.events.base import DomainEvent


@dataclass(frozen=True, kw_only=True)
class AIUsageRecorded(DomainEvent):
    usage_id: UUID
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    estimated_cost: Decimal
    workflow_execution_id: UUID | None = None
    agent_id: UUID | None = None


@dataclass(frozen=True, kw_only=True)
class WorkflowExecutionFinished(DomainEvent):
    execution_id: UUID
    workflow_id: UUID
    status: str
    duration_ms: int


@dataclass(frozen=True, kw_only=True)
class PromptUpdated(DomainEvent):
    prompt_id: UUID
    previous_values: dict
    current_values: dict


@dataclass(frozen=True, kw_only=True)
class BudgetThresholdCrossed(DomainEvent):
    budget_id: UUID
    budget_name: str
    status: str
    usage_percent: float
    current_spend: Decimal
    monthly_limit: Decimal
    workflow_id: UUID | None = None
