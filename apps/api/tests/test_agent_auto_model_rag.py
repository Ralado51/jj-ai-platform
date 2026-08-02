from collections.abc import Iterator
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.agent_framework import AgentDescriptor, AgentRegistry, PromptAgent
from app.services.agent_service import AgentService
from app.services.chat_providers import ChatProvider
from app.services.model_router import AITaskType


class FakeProvider(ChatProvider):
    name = "fake"

    def __init__(self, model: str = "configured-model") -> None:
        self.model = model

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        return f"{self.model}: {user_prompt}"

    def stream_generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> Iterator[str]:
        yield self.generate(system_prompt=system_prompt, user_prompt=user_prompt)


class FakeSelector:
    def select(self, *, user_id, task):
        return SimpleNamespace(
            model="benchmark-winner",
            reason="Modelo selecionado pelo histórico de benchmarks.",
            source="benchmark_history",
        )


class FakeRagService:
    def answer(self, project_id, user_id, data):
        return SimpleNamespace(
            answer=f"Resposta fundamentada: {data.question}",
            chat_provider="ollama",
            chat_model="rag-winner",
            routing=SimpleNamespace(reason="Modelo RAG selecionado automaticamente."),
        )


def fake_settings():
    return SimpleNamespace(
        ollama_chat_model="default-model",
        ollama_content_model="",
        ollama_rag_model="",
        ollama_coding_model="",
        ollama_summarization_model="",
        ollama_general_model="",
        ollama_base_url="http://ollama:11434",
        ollama_chat_timeout_seconds=180.0,
        ollama_chat_temperature=0.2,
        ollama_chat_max_tokens=2048,
        ollama_chat_repeat_penalty=1.12,
        ollama_chat_max_characters=24000,
        auto_model_selection_enabled=True,
        auto_model_minimum_samples=3,
        auto_model_minimum_average_score=7.0,
    )


def build_registry() -> AgentRegistry:
    registry = AgentRegistry()
    registry.register(
        PromptAgent(
            descriptor=AgentDescriptor(
                id="general",
                name="General",
                description="General",
                task=AITaskType.GENERAL,
            ),
            provider=FakeProvider(),
            system_prompt="Sistema geral",
        )
    )
    registry.register(
        PromptAgent(
            descriptor=AgentDescriptor(
                id="rag",
                name="RAG",
                description="Documentos",
                task=AITaskType.RAG,
                keywords=("documento",),
            ),
            provider=FakeProvider("rag-configured"),
            system_prompt="Sistema RAG",
        )
    )
    return registry


def test_agent_uses_task_scoped_benchmark_winner(monkeypatch) -> None:
    monkeypatch.setattr("app.services.agent_service.get_settings", fake_settings)
    service = AgentService(registry=build_registry(), auto_selector=FakeSelector())
    service._build_provider = lambda model: FakeProvider(model)

    response = service.run(
        instruction="Explique a arquitetura.",
        agent_id="general",
        user_id=uuid4(),
    )

    assert response.model == "benchmark-winner"
    assert response.model_selection_source == "benchmark_history"
    assert "histórico de benchmarks" in response.routing_reason


def test_rag_agent_requires_project_id(monkeypatch) -> None:
    monkeypatch.setattr("app.services.agent_service.get_settings", fake_settings)
    service = AgentService(registry=build_registry(), rag_service=FakeRagService())

    with pytest.raises(ValueError, match="project_id"):
        service.run(
            instruction="O que diz o documento?",
            agent_id="rag",
            user_id=uuid4(),
        )


def test_rag_agent_uses_project_runtime(monkeypatch) -> None:
    monkeypatch.setattr("app.services.agent_service.get_settings", fake_settings)
    service = AgentService(registry=build_registry(), rag_service=FakeRagService())
    project_id = uuid4()

    response = service.run(
        instruction="O que diz o documento?",
        agent_id="rag",
        user_id=uuid4(),
        project_id=project_id,
    )

    assert response.agent.id == "rag"
    assert response.project_id == project_id
    assert response.model == "rag-winner"
    assert response.model_selection_source == "rag_runtime"
    assert "Resposta fundamentada" in response.content
