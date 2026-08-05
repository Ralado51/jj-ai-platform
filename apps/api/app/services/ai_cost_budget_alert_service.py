from __future__ import annotations

import datetime as dt
from uuid import UUID

from app.repositories.ai_cost_budget_repository import AICostBudgetRepository
from app.repositories.notification_repository import NotificationRepository
from app.services.ai_cost_budget_service import AICostBudgetService


class AICostBudgetAlertService:
    """Create deduplicated in-app notifications when active budgets cross thresholds."""

    def __init__(self, *, budget_repository: AICostBudgetRepository, notification_repository: NotificationRepository) -> None:
        self.budget_repository = budget_repository
        self.notification_repository = notification_repository
        self.budget_service = AICostBudgetService(budget_repository, budget_repository.db)

    def evaluate(self, *, user_id: UUID) -> list:
        created = []
        month_key = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m")
        for budget in self.budget_repository.list(user_id=user_id):
            if not budget.is_active:
                continue
            status = self.budget_service.status(user_id=user_id, budget=budget)
            state = status["status"]
            if state == "healthy":
                continue

            usage = float(status["usage_percent"])
            spend = status["current_spend"]
            limit = status["monthly_limit"]
            severity = "critical" if state == "critical" else "warning"
            title = (
                f"Budget crítico: {budget.name}"
                if state == "critical"
                else f"Budget em alerta: {budget.name}"
            )
            message = (
                f"O budget {budget.name} atingiu {usage:.2f}% do limite mensal "
                f"(US$ {spend} de US$ {limit})."
            )
            item = self.notification_repository.create_if_absent(
                user_id=user_id,
                type="ai_cost_budget",
                severity=severity,
                title=title,
                message=message,
                deduplication_key=f"ai-cost-budget:{budget.id}:{month_key}:{state}",
                workflow_id=budget.scope_id if budget.scope_type == "workflow" else None,
            )
            created.append(item)
        return created
