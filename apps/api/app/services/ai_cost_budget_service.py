from __future__ import annotations

import datetime as dt
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai_cost_budget import AICostBudget
from app.models.ai_usage import AIUsage
from app.models.workflow_execution import WorkflowExecution
from app.repositories.ai_cost_budget_repository import AICostBudgetRepository


class AICostBudgetService:
    def __init__(self, repository: AICostBudgetRepository, db: Session) -> None:
        self.repository = repository
        self.db = db

    @staticmethod
    def _month_bounds(now: dt.datetime | None = None) -> tuple[dt.datetime, dt.datetime]:
        current = now or dt.datetime.now(dt.timezone.utc)
        start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        return start, end

    def current_spend(self, *, user_id: UUID, budget: AICostBudget) -> Decimal:
        start, end = self._month_bounds()
        query = select(func.coalesce(func.sum(AIUsage.estimated_cost), 0)).where(
            AIUsage.user_id == user_id,
            AIUsage.created_at >= start,
            AIUsage.created_at < end,
        )
        if budget.scope_type == "project":
            query = query.where(AIUsage.project_id == budget.scope_id)
        elif budget.scope_type == "workflow":
            query = query.join(WorkflowExecution, WorkflowExecution.id == AIUsage.workflow_execution_id).where(
                WorkflowExecution.workflow_id == budget.scope_id
            )
        return Decimal(self.db.scalar(query) or 0)

    def status(self, *, user_id: UUID, budget: AICostBudget) -> dict:
        spend = self.current_spend(user_id=user_id, budget=budget)
        limit = Decimal(budget.monthly_limit)
        usage = float((spend / limit) * 100) if limit else 0.0
        if usage >= budget.critical_threshold_percent:
            state = "critical"
        elif usage >= budget.warning_threshold_percent:
            state = "warning"
        else:
            state = "healthy"
        return {
            **{column.name: getattr(budget, column.name) for column in budget.__table__.columns if column.name not in {"user_id", "created_at", "updated_at"}},
            "current_spend": spend,
            "usage_percent": round(usage, 2),
            "remaining": max(Decimal("0"), limit - spend),
            "status": state,
        }

    def list_statuses(self, *, user_id: UUID) -> list[dict]:
        return [self.status(user_id=user_id, budget=item) for item in self.repository.list(user_id=user_id)]
