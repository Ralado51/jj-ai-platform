from __future__ import annotations

import datetime as dt
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification_email_delivery import NotificationEmailDelivery


class NotificationEmailDeliveryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create(
        self,
        *,
        user_id: UUID,
        recipient: str,
        deduplication_key: str,
        workflow_id: UUID | None = None,
    ) -> NotificationEmailDelivery:
        item = self.db.scalar(
            select(NotificationEmailDelivery).where(
                NotificationEmailDelivery.user_id == user_id,
                NotificationEmailDelivery.deduplication_key == deduplication_key,
            )
        )
        if item is not None:
            return item
        item = NotificationEmailDelivery(
            user_id=user_id,
            workflow_id=workflow_id,
            recipient=recipient,
            deduplication_key=deduplication_key,
            status="pending",
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def mark_sent(self, item: NotificationEmailDelivery) -> NotificationEmailDelivery:
        item.status = "sent"
        item.sent_at = dt.datetime.now(dt.UTC)
        item.error_message = None
        self.db.commit()
        self.db.refresh(item)
        return item

    def mark_failed(self, item: NotificationEmailDelivery, error_message: str) -> NotificationEmailDelivery:
        item.status = "failed"
        item.error_message = error_message[:2000]
        self.db.commit()
        self.db.refresh(item)
        return item
