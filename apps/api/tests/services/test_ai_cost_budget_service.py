from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.services.ai_cost_budget_service import AICostBudgetService


class _Repository:
    def list(self, *, user_id):
        return []


class _DB:
    def __init__(self, value):
        self.value = value

    def scalar(self, query):
        return self.value


def test_budget_status_marks_warning():
    budget = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        scope_type="global",
        scope_id=None,
        name="Global",
        monthly_limit=Decimal("100"),
        warning_threshold_percent=80,
        critical_threshold_percent=100,
        is_active=True,
        __table__=SimpleNamespace(columns=[]),
    )
    service = AICostBudgetService(_Repository(), _DB(Decimal("85")))
    result = service.status(user_id=budget.user_id, budget=budget)

    assert result["status"] == "warning"
    assert result["usage_percent"] == 85.0
    assert result["remaining"] == Decimal("15")
