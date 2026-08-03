import datetime as dt
from uuid import uuid4

from app.schemas.analytics import WorkflowHealthHistoryResponse


def test_workflow_health_history_response_contract() -> None:
    response = WorkflowHealthHistoryResponse.model_validate(
        {
            "id": uuid4(),
            "workflow_id": uuid4(),
            "workflow_name": "Conteúdo",
            "snapshot_date": dt.date(2026, 8, 3),
            "health_score": 88,
            "health_label": "Bom",
            "executions": 12,
            "success_rate": 91.67,
            "retry_rate": 8.33,
            "average_duration_ms": 4200,
            "bottleneck_step": 2,
            "bottleneck_share": 54.2,
        }
    )

    assert response.health_score == 88
    assert response.snapshot_date == dt.date(2026, 8, 3)
