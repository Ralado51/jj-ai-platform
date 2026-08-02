from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_workflow import AgentWorkflow


class AgentWorkflowRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, *, user_id: UUID, project_id: UUID | None = None, active_only: bool = True) -> list[AgentWorkflow]:
        statement = select(AgentWorkflow).where(AgentWorkflow.user_id == user_id)
        if project_id is not None:
            statement = statement.where(AgentWorkflow.project_id == project_id)
        if active_only:
            statement = statement.where(AgentWorkflow.is_active.is_(True))
        statement = statement.order_by(AgentWorkflow.updated_at.desc())
        return list(self.db.scalars(statement).all())

    def get(self, *, workflow_id: UUID, user_id: UUID) -> AgentWorkflow | None:
        return self.db.scalar(
            select(AgentWorkflow).where(
                AgentWorkflow.id == workflow_id,
                AgentWorkflow.user_id == user_id,
            )
        )

    def create(self, workflow: AgentWorkflow) -> AgentWorkflow:
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)
        return workflow

    def save(self, workflow: AgentWorkflow) -> AgentWorkflow:
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)
        return workflow
