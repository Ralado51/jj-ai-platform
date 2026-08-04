import datetime as dt
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.services.ai_cost_optimizer_service import AICostOptimizerService


class _Repository:
    def __init__(self, items):
        self.items = items

    def list(self, **_kwargs):
        return self.items


def _usage(index: int):
    return SimpleNamespace(
        created_at=dt.datetime(2026, 8, 1, 12, index, tzinfo=dt.UTC),
        provider="openai",
        model="gpt-4o-mini",
        total_tokens=1000,
        estimated_cost=Decimal("0.10"),
        equivalent_openai_cost=Decimal("0.10"),
        latency_ms=3000,
        cached_response=False,
        project_id=None,
        agent_id=None,
        workflow_execution_id=None,
    )


def test_optimizer_generates_explainable_recommendations():
    result = AICostOptimizerService(_Repository([_usage(index) for index in range(10)])).recommendations(user_id=uuid4())

    categories = {item["category"] for item in result["recommendations"]}
    assert {"cache", "model", "provider", "latency", "trend"}.issubset(categories)
    assert result["potential_monthly_savings"] == Decimal("0.800000")
    assert result["recommendations"][0]["priority"] == "high"
    assert all(0 <= item["confidence"] <= 1 for item in result["recommendations"])


def test_optimizer_returns_empty_result_without_history():
    result = AICostOptimizerService(_Repository([])).recommendations(user_id=uuid4())

    assert result == {"potential_monthly_savings": Decimal("0"), "recommendations": []}
