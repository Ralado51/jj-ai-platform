from __future__ import annotations

import datetime as dt
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditLogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_once(self, *, values: dict) -> AuditLog | None:
        item = AuditLog(**values)
        self.db.add(item)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            return None
        self.db.refresh(item)
        return item

    def has_entity_event(self, *, entity_type: str | None, entity_id: UUID | None) -> bool:
        if entity_type is None or entity_id is None:
            return False
        return bool(
            self.db.scalar(
                select(AuditLog.id)
                .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
                .limit(1)
            )
        )

    def list(
        self,
        *,
        actor_id: UUID | None = None,
        project_id: UUID | None = None,
        event_name: str | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        occurred_from: dt.datetime | None = None,
        occurred_to: dt.datetime | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[AuditLog], int]:
        statement = select(AuditLog)
        if actor_id is not None:
            statement = statement.where(AuditLog.actor_id == actor_id)
        if project_id is not None:
            statement = statement.where(AuditLog.project_id == project_id)
        if event_name:
            statement = statement.where(AuditLog.event_name == event_name)
        if action:
            statement = statement.where(AuditLog.action == action)
        if entity_type:
            statement = statement.where(AuditLog.entity_type == entity_type)
        if entity_id is not None:
            statement = statement.where(AuditLog.entity_id == entity_id)
        if occurred_from is not None:
            statement = statement.where(AuditLog.occurred_at >= occurred_from)
        if occurred_to is not None:
            statement = statement.where(AuditLog.occurred_at <= occurred_to)
        total = int(self.db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
        items = list(
            self.db.scalars(
                statement.order_by(AuditLog.occurred_at.desc(), AuditLog.created_at.desc())
                .offset(offset)
                .limit(limit)
            ).all()
        )
        return items, total
