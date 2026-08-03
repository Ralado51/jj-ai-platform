from types import SimpleNamespace
from uuid import uuid4

from app.services.workflow_analytics_service import WorkflowAnalyticsService


class _Repository:
    def __init__(self, items):
        self.items = items

    def list(self, **_kwargs):
        return self.items


def test_workflow_analytics_aggregates_execution_and_step_metrics():
    workflow_id = uuid4()
    items = [
        SimpleNamespace(
            workflow_id=workflow_id,
            workflow_name="Conteúdo",
            status="completed",
            total_duration_ms=3000,
            parent_execution_id=None,
            steps_completed=2,
            steps_total=2,
            error_message=None,
            step_details=[
                {"index": 1, "agent_id": "rag", "agent_name": "RAG", "duration_ms": 1000},
                {"index": 2, "agent_id": "writer", "agent_name": "Writer", "duration_ms": 2000},
            ],
        ),
        SimpleNamespace(
            workflow_id=workflow_id,
            workflow_name="Conteúdo",
            status="failed",
            total_duration_ms=1000,
            parent_execution_id=uuid4(),
            steps_completed=1,
            steps_total=2,
            error_message="Falha no modelo",
            step_details=[
                {"index": 1, "agent_id": "rag", "agent_name": "RAG", "duration_ms": 1000},
            ],
        ),
    ]

    result = WorkflowAnalyticsService(_Repository(items)).summary(user_id=uuid4())

    assert result.total_executions == 2
    assert result.completed_executions == 1
    assert result.failed_executions == 1
    assert result.retry_executions == 1
    assert result.success_rate == 50.0
    assert result.average_duration_ms == 3000
    assert result.workflows[0].executions == 2
    assert result.slowest_steps[0].agent_id == "writer"
    assert result.failure_points[0].step == 2
