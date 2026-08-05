from __future__ import annotations

from time import perf_counter
from uuid import UUID

from fastapi import HTTPException, status

from app.events.bus import DomainEventBus, domain_event_bus
from app.events.types import PlaygroundRunFinished
from app.models.playground import PlaygroundRun, PlaygroundSession
from app.repositories.playground_repository import PlaygroundRepository
from app.schemas.playground import PlaygroundRunCreate
from app.services.agent_orchestrator import AgentOrchestrationStep, AgentOrchestrator
from app.services.agent_service import AgentService


class PlaygroundService:
    def __init__(
        self,
        repository: PlaygroundRepository,
        *,
        agent_service: AgentService,
        event_bus: DomainEventBus = domain_event_bus,
    ) -> None:
        self.repository = repository
        self.agent_service = agent_service
        self.event_bus = event_bus

    def create_session(
        self, *, owner_id: UUID, project_id: UUID | None, name: str
    ) -> PlaygroundSession:
        return self.repository.create_session(
            owner_id=owner_id, project_id=project_id, name=name.strip()
        )

    def get_session(
        self, *, session_id: UUID, owner_id: UUID
    ) -> PlaygroundSession:
        session = self.repository.get_session(
            session_id=session_id, owner_id=owner_id
        )
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Playground session not found.",
            )
        return session

    def run(
        self,
        *,
        session: PlaygroundSession,
        payload: PlaygroundRunCreate,
        owner_id: UUID,
    ) -> PlaygroundRun:
        started_at = perf_counter()
        output = ""
        step_results: list[dict] = []
        provider = None
        model = None
        error = None
        run_status = "completed"

        try:
            if payload.mode == "agent":
                result = self.agent_service.run(
                    instruction=payload.input,
                    agent_id=payload.agent_id,
                    user_id=owner_id,
                    project_id=session.project_id,
                    session_key=None,
                    use_memory=False,
                )
                output = result.content
                provider = result.provider
                model = result.model
                step_results = [result.model_dump(mode="json")]
            else:
                result = AgentOrchestrator(self.agent_service).run(
                    initial_instruction=payload.input,
                    steps=[
                        AgentOrchestrationStep(
                            agent_id=item.agent_id,
                            instruction=item.instruction,
                        )
                        for item in payload.steps
                    ],
                    user_id=owner_id,
                    project_id=session.project_id,
                    session_key=None,
                    use_memory=False,
                )
                output = result.final_content
                step_results = [
                    item.model_dump(mode="json") for item in result.steps
                ]
                if result.steps:
                    provider = result.steps[-1].provider
                    model = result.steps[-1].model
        except Exception as exc:
            run_status = "failed"
            error = str(exc)[:2000]

        item = self.repository.create_run(
            values={
                "session_id": session.id,
                "owner_id": owner_id,
                "mode": payload.mode,
                "status": run_status,
                "input": payload.input,
                "output": output,
                "steps": step_results,
                "provider": provider,
                "model": model,
                "duration_ms": max(
                    0, round((perf_counter() - started_at) * 1000)
                ),
                "error": error,
            }
        )
        self.event_bus.publish(
            PlaygroundRunFinished(
                actor_id=owner_id,
                project_id=session.project_id,
                session_id=session.id,
                run_id=item.id,
                mode=payload.mode,
                status=run_status,
                duration_ms=item.duration_ms,
                provider=provider,
                model=model,
            )
        )
        return item
