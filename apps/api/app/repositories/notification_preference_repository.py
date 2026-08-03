from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification_preference import NotificationPreference


class NotificationPreferenceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create(self, *, user_id: UUID, default_email: str | None = None) -> NotificationPreference:
        item = self.db.scalar(select(NotificationPreference).where(NotificationPreference.user_id == user_id))
        if item is not None:
            return item
        item = NotificationPreference(user_id=user_id, email_address=default_email)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update(
        self,
        *,
        user_id: UUID,
        in_app_enabled: bool,
        email_enabled: bool,
        critical_only: bool,
        email_address: str | None,
        default_email: str | None = None,
    ) -> NotificationPreference:
        item = self.get_or_create(user_id=user_id, default_email=default_email)
        item.in_app_enabled = in_app_enabled
        item.email_enabled = email_enabled
        item.critical_only = critical_only
        item.email_address = email_address
        self.db.commit()
        self.db.refresh(item)
        return item
