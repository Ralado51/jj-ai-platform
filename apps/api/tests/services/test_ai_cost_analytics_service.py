import datetime as dt
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.services.ai_cost_analytics_service import AICostAnalyticsService


class _Repository:
    def __init__(self, items):
        self.items = items

    def list(self, **_kwargs):
        return self.items


def _usage(*, day, provider, model, tokens, cost, equivalent, latency, cached=False, project_id=None, agent_id=None, workflow_execution_id=None):
    return SimpleNamespace(
        created_at=dt.datetime.combine(day, dt.time(12, 0), tzinfo=dt.UTC),
        provider=provider,
        model=model,
        total_tokens=tokens,
        estimated_cost=Decimal(cost),
        equivalent_openai_cost=Decimal(equivalent),
        latency_ms=latency,
        cached_response=cached,
        project_id=project_id,
        agent_id=agent_id,
        workflow_execution_id=workflow_execution_id,
    )


def test_dashboard_aggregates_usage_and_rankings():
    project_id = uuid4()
    agent_id = uuid4()
    workflow_id = uuid4()
    items = [
        _usage(day=dt.date(2026, 8, 1), provider="ollama", model="qwen", tokens=1000, cost="0", equivalent="0.01", latency=800, cached=True, project_id=project_id, agent_id=agent_id, workflow_execution_id=workflow_id),
        _usage(day=dt.date(2026, 8, 2), provider="openai", model="gpt-4o-mini", tokens=2000, cost="0.02", equivalent="0.02", latency=1200, project_id=project_id, agent_id=agent_id, workflow_execution_id=workflow_id),
    ]

    result = AICostAnalyticsService(_Repository(items)).dashboard(user_id=uuid4())

    assert result["summary"]["total_requests"] == 2
    assert result["summary"]["total_tokens"] == 3000
    assert result["summary"]["estimated_cost"] == Decimal("0.02")
    assert result["summary"]["ollama_savings"] == Decimal("0.01")
    assert result["summary"]["cache_hit_rate"] == 50.0
    assert len(result["timeline"]) == 2
    assert result["models"][0]["key"] == "gpt-4o-mini"
    assert result["projects"][0]["key"] == str(project_id)
    assert result["agents"][0]["key"] == str(agent_id)
    assert result["workflows"][0]["key"] == str(workflow_id)


def test_dashboard_handles_empty_history():
    result = AICostAnalyticsService(_Repository([])).dashboard(user_id=uuid4())

    assert result["summary"]["total_requests"] == 0
    assert result["summary"]["cache_hit_rate"] == 0.0
    assert result["timeline"] == []
    assert result["trends"]["weekly_cost_growth"] == 0.0
