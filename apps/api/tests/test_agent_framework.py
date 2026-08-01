from collections.abc import Iterator

import pytest

from app.services.agent_framework import (
    AgentDescriptor,
    AgentRegistry,
    AgentRouter,
    PromptAgent,
)
from app.services.chat_providers import ChatProvider
from app.services.model_router import AITaskType


class FakeProvider(ChatProvider):
    name = "fake"
    model = "fake-model"

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        return f"{system_prompt} | {user_prompt}"

    def stream_generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> Iterator[str]:
        yield self.generate(system_prompt=system_prompt, user_prompt=user_prompt)


def build_agent(agent_id: str, task: AITaskType, keywords=()):
    return PromptAgent(
        descriptor=AgentDescriptor(
            id=agent_id,
            name=agent_id,
            description=f"Agente {agent_id}",
            task=task,
            keywords=keywords,
        ),
        provider=FakeProvider(),
        system_prompt=f"Sistema {agent_id}",
    )


def build_registry() -> AgentRegistry:
    registry = AgentRegistry()
    registry.register(build_agent("general", AITaskType.GENERAL))
    registry.register(
        build_agent(
            "code-review",
            AITaskType.CODING,
            keywords=("código", "bug", "python"),
        )
    )
    registry.register(
        build_agent(
            "summarizer",
            AITaskType.SUMMARIZATION,
            keywords=("resuma", "resumo"),
        )
    )
    return registry


def test_routes_to_specialized_agent_by_instruction() -> None:
    route = AgentRouter(build_registry()).route(
        instruction="Encontre o bug neste código Python."
    )

    assert route.agent.descriptor.id == "code-review"
    assert "correspondência" in route.reason


def test_uses_explicit_agent_selection() -> None:
    route = AgentRouter(build_registry()).route(
        instruction="Faça o trabalho.",
        agent_id="summarizer",
    )

    assert route.agent.descriptor.id == "summarizer"
    assert "explicitamente" in route.reason


def test_falls_back_to_general_agent() -> None:
    route = AgentRouter(build_registry()).route(
        instruction="Ajude com uma pergunta qualquer."
    )

    assert route.agent.descriptor.id == "general"


def test_prompt_agent_executes_provider() -> None:
    agent = build_agent("general", AITaskType.GENERAL)

    result = agent.execute(instruction="Explique o projeto.")

    assert result.agent.id == "general"
    assert result.provider == "fake"
    assert result.model == "fake-model"
    assert "Explique o projeto." in result.content


def test_registry_rejects_duplicate_agent_ids() -> None:
    registry = AgentRegistry()
    registry.register(build_agent("general", AITaskType.GENERAL))

    with pytest.raises(ValueError, match="already registered"):
        registry.register(build_agent("general", AITaskType.GENERAL))
