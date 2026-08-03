from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from uuid import UUID

from app.schemas.agents import AgentRunResponse
from app.services.agent_service import AgentService


@dataclass(frozen=True)
class AgentOrchestrationStep:
    agent_id: str
    instruction: str | None = None


@dataclass(frozen=True)
class AgentOrchestrationResult:
    steps: list[AgentRunResponse]
    final_content: str
    total_duration_ms: int


class AgentOrchestrationCancelled(RuntimeError):
    def __init__(self, completed_steps: list[AgentRunResponse]) -> None:
        super().__init__("workflow execution cancelled")
        self.completed_steps = completed_steps


class AgentOrchestrator:
    """Executes an explicit sequence of agents and forwards each output to the next step."""

    def __init__(self, service: AgentService) -> None:
        self.service = service

    def run(
        self,
        *,
        initial_instruction: str,
        steps: list[AgentOrchestrationStep],
        user_id: UUID,
        project_id: UUID | None = None,
        session_key: str | None = None,
        use_memory: bool = True,
        should_cancel: Callable[[], bool] | None = None,
        on_step_completed: Callable[[int, AgentRunResponse], None] | None = None,
    ) -> AgentOrchestrationResult:
        if not steps:
            raise ValueError("at least one orchestration step is required")
        if len(steps) > 6:
            raise ValueError("an orchestration can contain at most 6 steps")

        current_content = initial_instruction.strip()
        results: list[AgentRunResponse] = []

        for index, step in enumerate(steps, start=1):
            if should_cancel is not None and should_cancel():
                raise AgentOrchestrationCancelled(results.copy())

            instruction = self._build_instruction(
                step_number=index,
                step_instruction=step.instruction,
                previous_content=current_content,
            )
            result = self.service.run(
                instruction=instruction,
                agent_id=step.agent_id,
                user_id=user_id,
                project_id=project_id,
                session_key=session_key,
                use_memory=use_memory,
            )
            results.append(result)
            current_content = result.content

            if on_step_completed is not None:
                on_step_completed(index, result)

            if should_cancel is not None and should_cancel():
                raise AgentOrchestrationCancelled(results.copy())

        return AgentOrchestrationResult(
            steps=results,
            final_content=current_content,
            total_duration_ms=sum(item.duration_ms for item in results),
        )

    @staticmethod
    def _build_instruction(
        *,
        step_number: int,
        step_instruction: str | None,
        previous_content: str,
    ) -> str:
        objective = (step_instruction or "Processe o conteúdo recebido conforme sua especialidade.").strip()
        if step_number == 1:
            return f"OBJETIVO DA ETAPA\n{objective}\n\nENTRADA\n{previous_content}"
        return (
            f"OBJETIVO DA ETAPA {step_number}\n{objective}\n\n"
            "SAÍDA DA ETAPA ANTERIOR\n"
            f"{previous_content}\n\n"
            "Trabalhe sobre a saída anterior sem inventar fatos que não estejam nela."
        )
