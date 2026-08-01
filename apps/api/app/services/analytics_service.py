from __future__ import annotations

from uuid import UUID

from app.repositories.benchmark_repository import BenchmarkRepository
from app.schemas.analytics import AIAnalyticsSummaryResponse
from app.services.model_router import AITaskType


class AnalyticsService:
    def __init__(self, repository: BenchmarkRepository) -> None:
        self.repository = repository

    def summary(
        self,
        *,
        user_id: UUID,
        task: AITaskType | None = None,
    ) -> AIAnalyticsSummaryResponse:
        return AIAnalyticsSummaryResponse.model_validate(
            self.repository.summary(user_id=user_id, task=task)
        )
