from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.schemas.agents import AgentDescriptorResponse, AgentRunResponse
from app.services.agent_orchestrator import AgentOrchestrationStep, AgentOrchestrator
from app.services.model_router import AITaskType


class FakeAgentService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def run(self, **kwargs) -> AgentRunResponse:
        self.calls.append(kwargs)
        agent_id = kwargs["agent_id"]
        content = f"saida-{agent_id}-{len(self.calls)}"
        return AgentRunResponse(
            execution_id=uuid4(),
            agent=AgentDescriptorResponse(
                id=agent_id,
                name=agent_id,
                description="Agente de teste",
                task=AITaskType.GENERAL,
            ),
            routing_reason="teste",
            content=content,
            provider="fake",
            model="fake-model",
            duration_ms=100 * len(self.calls),
            session_key=kwargs.get("session_key"),
            project_id=kwargs.get("project_id"),
        )


def test_orchestrator_forwards_previous_output_to_next_agent() -> None:
    service = FakeAgentService()
    orchestrator = AgentOrchestrator(service)  # type: ignore[arg-type]
    user_id = uuid4()

    result = orchestrator.run(
        initial_instruction="Pesquise guard-rails em IA.",
        steps=[
            AgentOrchestrationStep("summarizer", "Extraia os pontos principais."),
            AgentOrchestrationStep("content-creator", "Crie um roteiro curto."),
        ],
        user_id=user_id,
        session_key="pipeline-01",
    )

    assert len(result.steps) == 2
    assert "Pesquise guard-rails em IA" in service.calls[0]["instruction"]
    assert "saida-summarizer-1" in service.calls[1]["instruction"]
    assert result.final_content == "saida-content-creator-2"
    assert result.total_duration_ms == 300
    assert all(call["user_id"] == user_id for call in service.calls)
    assert all(call["session_key"] == "pipeline-01" for call in service.calls)


def test_orchestrator_passes_project_to_rag_step() -> None:
    service = FakeAgentService()
    project_id = uuid4()

    AgentOrchestrator(service).run(  # type: ignore[arg-type]
        initial_instruction="Analise o contrato.",
        steps=[AgentOrchestrationStep("rag", "Busque a cláusula 5.")],
        user_id=uuid4(),
        project_id=project_id,
    )

    assert service.calls[0]["project_id"] == project_id
    assert service.calls[0]["agent_id"] == "rag"


def test_orchestrator_rejects_empty_or_excessive_steps() -> None:
    orchestrator = AgentOrchestrator(FakeAgentService())  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="at least one"):
        orchestrator.run(
            initial_instruction="Teste",
            steps=[],
            user_id=uuid4(),
        )

    with pytest.raises(ValueError, match="at most 6"):
        orchestrator.run(
            initial_instruction="Teste",
            steps=[AgentOrchestrationStep("general") for _ in range(7)],
            user_id=uuid4(),
        )
