from __future__ import annotations

import datetime as dt

from app.repositories.workflow_execution_repository import WorkflowExecutionRepository
from app.repositories.workflow_health_history_repository import WorkflowHealthHistoryRepository
from app.services.workflow_insights_service import WorkflowInsightsService


class WorkflowHealthAutomationService:
    def __init__(
        self,
        execution_repository: WorkflowExecutionRepository,
        history_repository: WorkflowHealthHistoryRepository,
    ) -> None:
        self.execution_repository = execution_repository
        self.history_repository = history_repository

    def create_daily_snapshots(self, *, snapshot_date: dt.date | None = None) -> int:
        target_date = snapshot_date or dt.date.today()
        created = 0
        for user_id in self.execution_repository.list_user_ids():
            insights = WorkflowInsightsService(self.execution_repository).insights(user_id=user_id)
            for insight in insights.workflows:
                self.history_repository.upsert(
                    user_id=user_id,
                    insight=insight,
                    snapshot_date=target_date,
                )
                created += 1
        return created
