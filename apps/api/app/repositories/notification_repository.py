from __future__ import annotations

import datetime as dt
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.notification import Notification


class NotificationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_if_absent(
        self,
        *,
        user_id: UUID,
        type: str,
        severity: str,
        title: str,
        message: str,
        deduplication_key: str,
        workflow_id: UUID | None = None,
    ) -> Notification:
        item = self.db.scalar(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.deduplication_key == deduplication_key,
            )
        )
        if item is not None:
            return item
        item = Notification(
            user_id=user_id,
            type=type,
            severity=severity,
            title=title,
            message=message,
            workflow_id=workflow_id,
            deduplication_key=deduplication_key,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def _filtered_query(
        self,
        *,
        user_id: UUID,
        unread_only: bool = False,
        severity: str | None = None,
        type: str | None = None,
    ):
        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.is_read.is_(False))
        if severity:
            query = query.where(Notification.severity == severity)
        if type:
            query = query.where(Notification.type == type)
        return query

    def list(
        self,
        *,
        user_id: UUID,
        unread_only: bool = False,
        severity: str | None = None,
        type: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Notification]:
        query = self._filtered_query(
            user_id=user_id,
            unread_only=unread_only,
            severity=severity,
            type=type,
        )
        query = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(query).all())

    def count(
        self,
        *,
        user_id: UUID,
        unread_only: bool = False,
        severity: str | None = None,
        type: str | None = None,
    ) -> int:
        filtered = self._filtered_query(
            user_id=user_id,
            unread_only=unread_only,
            severity=severity,
            type=type,
        ).subquery()
        return int(self.db.scalar(select(func.count()).select_from(filtered)) or 0)

    def unread_count(self, *, user_id: UUID) -> int:
        return int(self.db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == user_id, Notification.is_read.is_(False))) or 0)

    def mark_read(self, *, user_id: UUID, notification_id: UUID) -> Notification | None:
        item = self.db.scalar(select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id))
        if item is None:
            return None
        if not item.is_read:
            item.is_read = True
            item.read_at = dt.datetime.now(dt.UTC)
            self.db.commit()
            self.db.refresh(item)
        return item

    def mark_all_read(self, *, user_id: UUID) -> int:
        items = list(self.db.scalars(select(Notification).where(Notification.user_id == user_id, Notification.is_read.is_(False))).all())
        now = dt.datetime.now(dt.UTC)
        for item in items:
            item.is_read = True
            item.read_at = now
        self.db.commit()
        return len(items)
