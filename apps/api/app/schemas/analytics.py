from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class ModelAnalyticsResponse(BaseModel):
    model: str
    executions: int
    average_score: float
    average_duration_ms: int
    estimated_tokens: int


class ModelWinResponse(BaseModel):
    model: str
    wins: int


class AIAnalyticsSummaryResponse(BaseModel):
    total_runs: int
    total_results: int
    success_rate: float
    top_model: str | None
    models: list[ModelAnalyticsResponse]
    winners: list[ModelWinResponse]


class WorkflowPerformanceResponse(BaseModel):
    workflow_id: UUID
    workflow_name: str
    executions: int
    success_rate: float
    average_duration_ms: int


class WorkflowStepPerformanceResponse(BaseModel):
    agent_id: str
    agent_name: str
    position: int
    executions: int
    average_duration_ms: int


class WorkflowFailurePointResponse(BaseModel):
    workflow_name: str
    step: int
    occurrences: int
    error_message: str


class WorkflowAnalyticsResponse(BaseModel):
    total_executions: int
    terminal_executions: int
    completed_executions: int
    failed_executions: int
    cancelled_executions: int
    retry_executions: int
    success_rate: float
    average_duration_ms: int
    workflows: list[WorkflowPerformanceResponse]
    slowest_steps: list[WorkflowStepPerformanceResponse]
    failure_points: list[WorkflowFailurePointResponse]


class WorkflowRecommendationResponse(BaseModel):
    code: str
    severity: str
    title: str
    description: str
    action: str
    step: int | None = None
    agent_id: str | None = None
    model: str | None = None


class WorkflowInsightResponse(BaseModel):
    workflow_id: UUID
    workflow_name: str
    health_score: int
    health_label: str
    executions: int
    success_rate: float
    retry_rate: float
    average_duration_ms: int
    bottleneck_step: int | None = None
    bottleneck_share: float | None = None
    recommendations: list[WorkflowRecommendationResponse]


class WorkflowInsightsResponse(BaseModel):
    workflows: list[WorkflowInsightResponse]
