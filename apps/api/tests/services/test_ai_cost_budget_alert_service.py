from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.services.ai_cost_budget_alert_service import AICostBudgetAlertService


class _BudgetRepository:
    def __init__(self, items):
        self.items = items

    def list(self, *, user_id):
        return self.items


class _NotificationRepository:
    def __init__(self):
        self.calls = []

    def create_if_absent(self, **values):
        self.calls.append(values)
        return values


class _BudgetService:
    def __init__(self, statuses):
        self.statuses = statuses

    def status(self, *, user_id, budget):
        return self.statuses[budget.id]


def test_budget_alerts_create_warning_and_critical_notifications():
    warning = SimpleNamespace(id=uuid4(), name="Marketing", is_active=True, scope_type="project", scope_id=uuid4())
    critical = SimpleNamespace(id=uuid4(), name="Conteúdo", is_active=True, scope_type="workflow", scope_id=uuid4())
    notifications = _NotificationRepository()

    service = AICostBudgetAlertService.__new__(AICostBudgetAlertService)
    service.budget_repository = _BudgetRepository([warning, critical])
    service.notification_repository = notifications
    service.budget_service = _BudgetService({
        warning.id: {"status": "warning", "usage_percent": 82.5, "current_spend": Decimal("82.5"), "monthly_limit": Decimal("100")},
        critical.id: {"status": "critical", "usage_percent": 105, "current_spend": Decimal("52.5"), "monthly_limit": Decimal("50")},
    })

    result = service.evaluate(user_id=uuid4())

    assert len(result) == 2
    assert notifications.calls[0]["severity"] == "warning"
    assert notifications.calls[1]["severity"] == "critical"
    assert notifications.calls[1]["workflow_id"] == critical.scope_id
    assert ":warning" in notifications.calls[0]["deduplication_key"]
    assert ":critical" in notifications.calls[1]["deduplication_key"]


def test_budget_alerts_ignore_healthy_and_inactive_budgets():
    healthy = SimpleNamespace(id=uuid4(), name="Global", is_active=True, scope_type="global", scope_id=None)
    inactive = SimpleNamespace(id=uuid4(), name="Inativo", is_active=False, scope_type="global", scope_id=None)
    notifications = _NotificationRepository()

    service = AICostBudgetAlertService.__new__(AICostBudgetAlertService)
    service.budget_repository = _BudgetRepository([healthy, inactive])
    service.notification_repository = notifications
    service.budget_service = _BudgetService({
        healthy.id: {"status": "healthy", "usage_percent": 10, "current_spend": Decimal("1"), "monthly_limit": Decimal("10")},
    })

    assert service.evaluate(user_id=uuid4()) == []
    assert notifications.calls == []
