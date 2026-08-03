import datetime as dt
from uuid import uuid4

from app.schemas.notifications import NotificationResponse


def test_notification_response_contract() -> None:
    response = NotificationResponse.model_validate(
        {
            "id": uuid4(),
            "type": "workflow_health_regression",
            "severity": "critical",
            "title": "Regressão crítica",
            "message": "O Health Score caiu 20 pontos.",
            "workflow_id": uuid4(),
            "is_read": False,
            "read_at": None,
            "created_at": dt.datetime.now(dt.UTC),
        }
    )

    assert response.severity == "critical"
    assert response.is_read is False
