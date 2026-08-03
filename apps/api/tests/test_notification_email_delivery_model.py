from app.models.notification_email_delivery import NotificationEmailDelivery


def test_notification_email_delivery_contract():
    columns = NotificationEmailDelivery.__table__.columns

    assert columns["recipient"].type.length == 320
    assert columns["deduplication_key"].type.length == 255
    assert columns["status"].type.length == 20
    assert columns["sent_at"].nullable is True
    assert columns["error_message"].nullable is True
