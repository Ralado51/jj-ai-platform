from uuid import uuid4

from app.schemas.notifications import NotificationListResponse


def test_notification_list_includes_pagination_metadata():
    response = NotificationListResponse(
        items=[],
        unread_count=3,
        total=21,
        page=2,
        page_size=10,
        total_pages=3,
    )

    assert response.unread_count == 3
    assert response.total == 21
    assert response.page == 2
    assert response.page_size == 10
    assert response.total_pages == 3
