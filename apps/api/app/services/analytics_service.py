from __future__ import annotations

from uuid import UUID

from app.repositories.benchmark_repository import BenchmarkRepository
from app.schemas.analytics import AIAnalyticsSummaryResponse


class AnalyticsService:
    def __init__(self, repository: BenchmarkRepository) -> None:
        self.repository = repository

    def summary(self, *, user_id: UUID) -> AIAnalyticsSummaryResponse:
        return AIAnalyticsSummaryResponse.model_validate(
            self.repository.summary(user_id=user_id)
        )
