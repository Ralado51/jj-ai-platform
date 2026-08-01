from collections.abc import Iterator
from types import SimpleNamespace
from uuid import uuid4

from app.services.agent_framework import AgentDescriptor, AgentRegistry, PromptAgent
from app.services.agent_service import AgentService
from app.services.chat_providers import ChatProvider
from app.services.model_router import AITaskType


class FakeProvider(ChatProvider):
    name = "fake"
    model = "fake-model"

    def __init__(self) -> None:
        self.user_prompts: list[str] = []

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        del system_prompt
        self.user_prompts.append(user_prompt)
        return "Resposta persistida"

    def stream_generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> Iterator[str]:
        yield self.generate(system_prompt=system_prompt, user_prompt=user_prompt)


class FakeRepository:
    def __init__(self) -> None:
        self.saved = None

    def recent_memory(self, **kwargs):
        assert kwargs["agent_id"] == "general"
        return [
            SimpleNamespace(role="user", content="Meu projeto usa FastAPI."),
            SimpleNamespace(role="assistant", content="Entendido."),
        ]

    def save_execution(self, **kwargs):
        self.saved = kwargs
        return SimpleNamespace(id=uuid4())


def test_agent_uses_scoped_memory_and_persists_execution() -> None:
    provider = FakeProvider()
    registry = AgentRegistry()
    registry.register(
        PromptAgent(
            descriptor=AgentDescriptor(
                id="general",
                name="Geral",
                description="Assistente geral",
                task=AITaskType.GENERAL,
            ),
            provider=provider,
            system_prompt="Responda objetivamente.",
        )
    )
    repository = FakeRepository()
    service = AgentService(registry=registry, repository=repository)
    user_id = uuid4()

    result = service.run(
        instruction="Qual framework eu uso?",
        user_id=user_id,
        session_key="projeto-a",
    )

    assert "HISTÓRICO RECENTE DESTA SESSÃO" in provider.user_prompts[0]
    assert "Meu projeto usa FastAPI" in provider.user_prompts[0]
    assert result.memory_items_used == 2
    assert result.session_key == "projeto-a"
    assert repository.saved["user_id"] == user_id
    assert repository.saved["instruction"] == "Qual framework eu uso?"
    assert repository.saved["response"] == "Resposta persistida"


def test_agent_can_disable_memory_but_still_persist() -> None:
    provider = FakeProvider()
    registry = AgentRegistry()
    registry.register(
        PromptAgent(
            descriptor=AgentDescriptor(
                id="general",
                name="Geral",
                description="Assistente geral",
                task=AITaskType.GENERAL,
            ),
            provider=provider,
            system_prompt="Responda objetivamente.",
        )
    )
    repository = FakeRepository()
    service = AgentService(registry=registry, repository=repository)

    result = service.run(
        instruction="Nova pergunta",
        user_id=uuid4(),
        session_key="projeto-a",
        use_memory=False,
    )

    assert provider.user_prompts == ["Nova pergunta"]
    assert result.memory_items_used == 0
    assert repository.saved is not None
