from __future__ import annotations

import datetime as dt
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.workflow_health_history import WorkflowHealthHistory


class WorkflowHealthHistoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert(self, *, user_id: UUID, insight, snapshot_date: dt.date) -> WorkflowHealthHistory:
        item = self.db.scalar(
            select(WorkflowHealthHistory).where(
                WorkflowHealthHistory.user_id == user_id,
                WorkflowHealthHistory.workflow_id == insight.workflow_id,
                WorkflowHealthHistory.snapshot_date == snapshot_date,
            )
        )
        values = {
            "workflow_name": insight.workflow_name,
            "health_score": insight.health_score,
            "health_label": insight.health_label,
            "executions": insight.executions,
            "success_rate": insight.success_rate,
            "retry_rate": insight.retry_rate,
            "average_duration_ms": insight.average_duration_ms,
            "bottleneck_step": insight.bottleneck_step,
            "bottleneck_share": insight.bottleneck_share,
        }
        if item is None:
            item = WorkflowHealthHistory(user_id=user_id, workflow_id=insight.workflow_id, snapshot_date=snapshot_date, **values)
            self.db.add(item)
        else:
            for key, value in values.items():
                setattr(item, key, value)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list(self, *, user_id: UUID, workflow_id: UUID | None = None, limit: int = 365) -> list[WorkflowHealthHistory]:
        query = select(WorkflowHealthHistory).where(WorkflowHealthHistory.user_id == user_id)
        if workflow_id is not None:
            query = query.where(WorkflowHealthHistory.workflow_id == workflow_id)
        query = query.order_by(WorkflowHealthHistory.snapshot_date.desc()).limit(limit)
        return list(self.db.scalars(query).all())
