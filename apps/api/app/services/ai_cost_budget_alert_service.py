from __future__ import annotations

import datetime as dt
from uuid import UUID

from app.models.user import User
from app.repositories.ai_cost_budget_repository import AICostBudgetRepository
from app.repositories.notification_preference_repository import NotificationPreferenceRepository
from app.repositories.notification_repository import NotificationRepository
from app.services.ai_cost_budget_service import AICostBudgetService
from app.services.email_service import EmailService


class AICostBudgetAlertService:
    """Create deduplicated notifications when active budgets cross thresholds."""

    def __init__(
        self,
        *,
        budget_repository: AICostBudgetRepository,
        notification_repository: NotificationRepository,
        email_service: EmailService | None = None,
    ) -> None:
        self.budget_repository = budget_repository
        self.notification_repository = notification_repository
        self.budget_service = AICostBudgetService(budget_repository, budget_repository.db)
        self.email_service = email_service or EmailService()

    def _send_critical_email(
        self,
        *,
        user_id: UUID,
        budget_name: str,
        usage_percent: float,
        current_spend: str,
        monthly_limit: str,
    ) -> None:
        db = getattr(self.budget_repository, "db", None)
        if db is None:
            return
        user = db.get(User, user_id)
        default_email = user.email if user is not None else None
        preference = NotificationPreferenceRepository(db).get_or_create(
            user_id=user_id,
            default_email=default_email,
        )
        recipient = preference.email_address or default_email
        if not preference.email_enabled or not recipient:
            return
        try:
            self.email_service.send_ai_budget_critical(
                recipient=recipient,
                budget_name=budget_name,
                usage_percent=usage_percent,
                current_spend=current_spend,
                monthly_limit=monthly_limit,
            )
        except Exception:
            # E-mail delivery must not interrupt usage telemetry or in-app notifications.
            return

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
            deduplication_key = f"ai-cost-budget:{budget.id}:{month_key}:{state}"
            lookup = getattr(self.notification_repository, "get_by_deduplication_key", None)
            already_exists = bool(
                lookup(user_id=user_id, deduplication_key=deduplication_key)
                if callable(lookup)
                else False
            )
            item = self.notification_repository.create_if_absent(
                user_id=user_id,
                type="ai_cost_budget",
                severity=severity,
                title=title,
                message=message,
                deduplication_key=deduplication_key,
                workflow_id=budget.scope_id if budget.scope_type == "workflow" else None,
            )
            created.append(item)
            if state == "critical" and not already_exists:
                self._send_critical_email(
                    user_id=user_id,
                    budget_name=budget.name,
                    usage_percent=usage,
                    current_spend=str(spend),
                    monthly_limit=str(limit),
                )
        return created
