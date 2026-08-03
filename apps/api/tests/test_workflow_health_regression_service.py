import datetime as dt
from types import SimpleNamespace
from uuid import uuid4

from app.services.workflow_health_regression_service import WorkflowHealthRegressionService


class _Repository:
    def __init__(self, items):
        self.items = items

    def list(self, **_kwargs):
        return self.items


def test_detects_score_regression_above_threshold() -> None:
    workflow_id = uuid4()
    items = [
        SimpleNamespace(
            workflow_id=workflow_id,
            workflow_name="Conteúdo",
            snapshot_date=dt.date(2026, 8, 3),
            health_score=62,
        ),
        SimpleNamespace(
            workflow_id=workflow_id,
            workflow_name="Conteúdo",
            snapshot_date=dt.date(2026, 8, 2),
            health_score=78,
        ),
    ]

    result = WorkflowHealthRegressionService(_Repository(items), threshold=10).detect(
        user_id=uuid4()
    )

    assert len(result.items) == 1
    assert result.items[0].delta == -16
    assert result.items[0].severity == "warning"


def test_ignores_small_variation() -> None:
    workflow_id = uuid4()
    items = [
        SimpleNamespace(
            workflow_id=workflow_id,
            workflow_name="Conteúdo",
            snapshot_date=dt.date(2026, 8, 3),
            health_score=75,
        ),
        SimpleNamespace(
            workflow_id=workflow_id,
            workflow_name="Conteúdo",
            snapshot_date=dt.date(2026, 8, 2),
            health_score=80,
        ),
    ]

    result = WorkflowHealthRegressionService(_Repository(items), threshold=10).detect(
        user_id=uuid4()
    )

    assert result.items == []
