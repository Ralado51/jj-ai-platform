from __future__ import annotations

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
