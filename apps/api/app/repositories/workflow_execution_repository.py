from __future__ import annotations

from uuid import UUID

from sqlalchemy import distinct, select
from sqlalchemy.orm import Session

from app.models.workflow_execution import WorkflowExecution


class WorkflowExecutionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, execution: WorkflowExecution) -> WorkflowExecution:
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        return execution

    def save(self, execution: WorkflowExecution) -> WorkflowExecution:
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        return execution

    def list(
        self,
        *,
        user_id: UUID,
        workflow_id: UUID | None = None,
        limit: int = 50,
    ) -> list[WorkflowExecution]:
        statement = select(WorkflowExecution).where(WorkflowExecution.user_id == user_id)
        if workflow_id is not None:
            statement = statement.where(WorkflowExecution.workflow_id == workflow_id)
        statement = statement.order_by(WorkflowExecution.created_at.desc()).limit(limit)
        return list(self.db.scalars(statement).all())

    def list_user_ids(self) -> list[UUID]:
        statement = select(distinct(WorkflowExecution.user_id)).order_by(WorkflowExecution.user_id)
        return list(self.db.scalars(statement).all())

    def get(self, *, execution_id: UUID, user_id: UUID) -> WorkflowExecution | None:
        return self.db.scalar(
            select(WorkflowExecution).where(
                WorkflowExecution.id == execution_id,
                WorkflowExecution.user_id == user_id,
            )
        )
