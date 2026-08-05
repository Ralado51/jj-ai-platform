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
class PromptCreated(DomainEvent):
    owner_id: UUID
    prompt_id: UUID
    current_values: dict


@dataclass(frozen=True, kw_only=True)
class PromptUpdated(DomainEvent):
    owner_id: UUID
    prompt_id: UUID
    previous_values: dict
    current_values: dict


@dataclass(frozen=True, kw_only=True)
class PromptArchived(DomainEvent):
    owner_id: UUID
    prompt_id: UUID
    current_values: dict


@dataclass(frozen=True, kw_only=True)
class PromptEvaluationFinished(DomainEvent):
    evaluation_id: UUID
    prompt_id: UUID
    prompt_version: int | None
    status: str
    score: float
    provider: str
    model: str


@dataclass(frozen=True, kw_only=True)
class WorkflowCreated(DomainEvent):
    owner_id: UUID
    workflow_id: UUID
    current_values: dict


@dataclass(frozen=True, kw_only=True)
class WorkflowUpdated(DomainEvent):
    owner_id: UUID
    workflow_id: UUID
    previous_values: dict
    current_values: dict


@dataclass(frozen=True, kw_only=True)
class WorkflowArchived(DomainEvent):
    owner_id: UUID
    workflow_id: UUID
    current_values: dict


@dataclass(frozen=True, kw_only=True)
class WorkflowBenchmarkFinished(DomainEvent):
    benchmark_id: UUID
    workflow_id: UUID
    status: str
    candidate_versions: tuple[int, ...]
    winner_version: int | None


@dataclass(frozen=True, kw_only=True)
class PlaygroundRunFinished(DomainEvent):
    session_id: UUID
    run_id: UUID
    mode: str
    status: str
    duration_ms: int
    provider: str | None
    model: str | None


@dataclass(frozen=True, kw_only=True)
class BudgetThresholdCrossed(DomainEvent):
    budget_id: UUID
    budget_name: str
    status: str
    usage_percent: float
    current_spend: Decimal
    monthly_limit: Decimal
    workflow_id: UUID | None = None
