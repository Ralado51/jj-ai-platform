from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from app.repositories.workflow_health_history_repository import WorkflowHealthHistoryRepository
from app.schemas.analytics import WorkflowHealthRegressionResponse, WorkflowHealthRegressionsResponse


class WorkflowHealthRegressionService:
    def __init__(self, repository: WorkflowHealthHistoryRepository, threshold: int = 10) -> None:
        self.repository = repository
        self.threshold = threshold

    def detect(self, *, user_id: UUID, workflow_id: UUID | None = None) -> WorkflowHealthRegressionsResponse:
        history = self.repository.list(user_id=user_id, workflow_id=workflow_id, limit=1000)
        grouped: dict[UUID, list] = defaultdict(list)
        for item in history:
            grouped[item.workflow_id].append(item)

        regressions: list[WorkflowHealthRegressionResponse] = []
        for items in grouped.values():
            items.sort(key=lambda item: item.snapshot_date, reverse=True)
            if len(items) < 2:
                continue
            current, previous = items[0], items[1]
            delta = current.health_score - previous.health_score
            if delta <= -self.threshold:
                regressions.append(
                    WorkflowHealthRegressionResponse(
                        workflow_id=current.workflow_id,
                        workflow_name=current.workflow_name,
                        previous_date=previous.snapshot_date,
                        current_date=current.snapshot_date,
                        previous_score=previous.health_score,
                        current_score=current.health_score,
                        delta=delta,
                        severity="critical" if delta <= -20 else "warning",
                    )
                )
        regressions.sort(key=lambda item: item.delta)
        return WorkflowHealthRegressionsResponse(items=regressions)
