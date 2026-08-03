from types import SimpleNamespace
from uuid import uuid4

from app.services.workflow_insights_service import WorkflowInsightsService


class _Repository:
    def __init__(self, items):
        self.items = items

    def list(self, **_kwargs):
        return self.items


def test_workflow_insights_detects_bottleneck_and_retries():
    workflow_id = uuid4()
    parent_id = uuid4()
    items = [
        SimpleNamespace(
            workflow_id=workflow_id,
            workflow_name="Conteúdo",
            status="completed",
            total_duration_ms=10000,
            parent_execution_id=None,
            step_details=[
                {"index": 1, "agent_id": "rag", "model": "qwen", "duration_ms": 2000},
                {"index": 2, "agent_id": "writer", "model": "gemma", "duration_ms": 8000},
            ],
        ),
        SimpleNamespace(
            workflow_id=workflow_id,
            workflow_name="Conteúdo",
            status="failed",
            total_duration_ms=2000,
            parent_execution_id=parent_id,
            step_details=[{"index": 1, "agent_id": "rag", "model": "qwen", "duration_ms": 2000}],
        ),
    ]

    result = WorkflowInsightsService(_Repository(items)).insights(user_id=uuid4())
    insight = result.workflows[0]

    assert insight.workflow_id == workflow_id
    assert insight.success_rate == 50.0
    assert insight.retry_rate == 50.0
    assert insight.bottleneck_step == 2
    assert insight.bottleneck_share == 66.67
    assert insight.health_label in {"Atenção", "Crítico"}
    assert {item.code for item in insight.recommendations} >= {
        "low_success_rate",
        "high_retry_rate",
        "step_bottleneck",
        "insufficient_history",
    }


def test_workflow_insights_returns_healthy_recommendation():
    workflow_id = uuid4()
    items = [
        SimpleNamespace(
            workflow_id=workflow_id,
            workflow_name="Saudável",
            status="completed",
            total_duration_ms=1000,
            parent_execution_id=None,
            step_details=[{"index": 1, "agent_id": "writer", "model": "qwen", "duration_ms": 1000}],
        )
        for _ in range(3)
    ]

    result = WorkflowInsightsService(_Repository(items)).insights(user_id=uuid4())
    insight = result.workflows[0]

    assert insight.health_score == 100
    assert insight.health_label == "Excelente"
    assert insight.recommendations[0].code == "healthy_workflow"
