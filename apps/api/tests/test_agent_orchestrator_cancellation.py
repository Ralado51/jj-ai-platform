from uuid import uuid4

import pytest

from app.schemas.agents import AgentDescriptorResponse, AgentRunResponse
from app.services.agent_orchestrator import (
    AgentOrchestrationCancelled,
    AgentOrchestrationStep,
    AgentOrchestrator,
)
from app.services.model_router import AITaskType


class _FakeAgentService:
    def __init__(self) -> None:
        self.calls = 0

    def run(self, **_: object) -> AgentRunResponse:
        self.calls += 1
        return AgentRunResponse(
            agent=AgentDescriptorResponse(
                id="general",
                name="General",
                description="General agent",
                task=AITaskType.GENERAL,
            ),
            routing_reason="test",
            content=f"output-{self.calls}",
            provider="ollama",
            model="qwen2.5:3b",
            duration_ms=100,
        )


def test_orchestrator_stops_before_next_step_when_cancelled() -> None:
    service = _FakeAgentService()
    cancel_checks = 0

    def should_cancel() -> bool:
        nonlocal cancel_checks
        cancel_checks += 1
        return cancel_checks >= 2

    with pytest.raises(AgentOrchestrationCancelled) as exc_info:
        AgentOrchestrator(service).run(
            initial_instruction="Execute",
            steps=[
                AgentOrchestrationStep(agent_id="general"),
                AgentOrchestrationStep(agent_id="general"),
            ],
            user_id=uuid4(),
            should_cancel=should_cancel,
        )

    assert service.calls == 1
    assert len(exc_info.value.completed_steps) == 1
    assert exc_info.value.completed_steps[0].content == "output-1"


def test_orchestrator_reports_each_completed_step() -> None:
    service = _FakeAgentService()
    completed: list[tuple[int, str]] = []

    result = AgentOrchestrator(service).run(
        initial_instruction="Execute",
        steps=[
            AgentOrchestrationStep(agent_id="general"),
            AgentOrchestrationStep(agent_id="general"),
        ],
        user_id=uuid4(),
        on_step_completed=lambda index, response: completed.append((index, response.content)),
    )

    assert completed == [(1, "output-1"), (2, "output-2")]
    assert result.final_content == "output-2"
