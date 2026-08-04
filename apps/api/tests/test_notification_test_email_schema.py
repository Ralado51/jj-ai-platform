import datetime as dt

from app.schemas.notification_preferences import NotificationTestEmailResponse


def test_notification_test_email_response() -> None:
    sent_at = dt.datetime.now(dt.UTC)

    response = NotificationTestEmailResponse(
        status="sent",
        recipient="user@example.com",
        sent_at=sent_at,
    )

    assert response.status == "sent"
    assert str(response.recipient) == "user@example.com"
    assert response.sent_at == sent_at
