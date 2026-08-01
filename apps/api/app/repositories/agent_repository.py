from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.agent_execution import AgentExecution, AgentMemory


class AgentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def recent_memory(
        self,
        *,
        user_id: UUID,
        agent_id: str,
        session_key: str,
        limit: int = 8,
    ) -> list[AgentMemory]:
        rows = self.db.scalars(
            select(AgentMemory)
            .where(
                AgentMemory.user_id == user_id,
                AgentMemory.agent_id == agent_id,
                AgentMemory.session_key == session_key,
            )
            .order_by(AgentMemory.created_at.desc())
            .limit(limit)
        ).all()
        return list(reversed(rows))

    def save_execution(
        self,
        *,
        user_id: UUID,
        agent_id: str,
        task_type: str,
        session_key: str | None,
        instruction: str,
        response: str,
        routing_reason: str,
        provider: str,
        model: str,
        duration_ms: int,
    ) -> AgentExecution:
        execution = AgentExecution(
            user_id=user_id,
            agent_id=agent_id,
            task_type=task_type,
            session_key=session_key,
            instruction=instruction,
            response=response,
            routing_reason=routing_reason,
            provider=provider,
            model=model,
            duration_ms=duration_ms,
        )
        self.db.add(execution)
        if session_key:
            self.db.add_all(
                [
                    AgentMemory(
                        user_id=user_id,
                        agent_id=agent_id,
                        session_key=session_key,
                        role="user",
                        content=instruction,
                    ),
                    AgentMemory(
                        user_id=user_id,
                        agent_id=agent_id,
                        session_key=session_key,
                        role="assistant",
                        content=response,
                    ),
                ]
            )
        self.db.commit()
        self.db.refresh(execution)
        return execution

    def list_executions(
        self,
        *,
        user_id: UUID,
        agent_id: str | None = None,
        limit: int = 50,
    ) -> list[AgentExecution]:
        query = select(AgentExecution).where(AgentExecution.user_id == user_id)
        if agent_id:
            query = query.where(AgentExecution.agent_id == agent_id)
        return list(
            self.db.scalars(
                query.order_by(AgentExecution.created_at.desc()).limit(limit)
            ).all()
        )

    def clear_memory(
        self,
        *,
        user_id: UUID,
        agent_id: str,
        session_key: str,
    ) -> int:
        result = self.db.execute(
            delete(AgentMemory).where(
                AgentMemory.user_id == user_id,
                AgentMemory.agent_id == agent_id,
                AgentMemory.session_key == session_key,
            )
        )
        self.db.commit()
        return int(result.rowcount or 0)
