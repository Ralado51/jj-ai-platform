from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.services.chat_providers import ChatProvider
from app.services.model_router import AITaskType


@dataclass(frozen=True)
class AgentDescriptor:
    id: str
    name: str
    description: str
    task: AITaskType
    keywords: tuple[str, ...] = ()


@dataclass(frozen=True)
class AgentExecutionResult:
    agent: AgentDescriptor
    content: str
    provider: str
    model: str


class BaseAgent(ABC):
    descriptor: AgentDescriptor

    @abstractmethod
    def execute(self, *, instruction: str) -> AgentExecutionResult:
        raise NotImplementedError


class PromptAgent(BaseAgent):
    def __init__(
        self,
        *,
        descriptor: AgentDescriptor,
        provider: ChatProvider,
        system_prompt: str,
    ) -> None:
        self.descriptor = descriptor
        self.provider = provider
        self.system_prompt = system_prompt.strip()

    def execute(self, *, instruction: str) -> AgentExecutionResult:
        content = self.provider.generate(
            system_prompt=self.system_prompt,
            user_prompt=instruction.strip(),
        )
        return AgentExecutionResult(
            agent=self.descriptor,
            content=content,
            provider=self.provider.name,
            model=self.provider.model,
        )


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        agent_id = agent.descriptor.id.strip()
        if not agent_id:
            raise ValueError("agent id must not be empty")
        if agent_id in self._agents:
            raise ValueError(f"agent already registered: {agent_id}")
        self._agents[agent_id] = agent

    def get(self, agent_id: str) -> BaseAgent:
        try:
            return self._agents[agent_id]
        except KeyError as exc:
            raise KeyError(f"unknown agent: {agent_id}") from exc

    def list(self) -> list[BaseAgent]:
        return list(self._agents.values())


@dataclass(frozen=True)
class AgentRoute:
    agent: BaseAgent
    reason: str


class AgentRouter:
    def __init__(self, registry: AgentRegistry, *, default_agent_id: str = "general") -> None:
        self.registry = registry
        self.default_agent_id = default_agent_id
        self.registry.get(default_agent_id)

    def route(self, *, instruction: str, agent_id: str | None = None) -> AgentRoute:
        if agent_id:
            agent = self.registry.get(agent_id)
            return AgentRoute(
                agent=agent,
                reason=f"Agente {agent_id} selecionado explicitamente.",
            )

        normalized = " ".join(instruction.lower().split())
        best_agent: BaseAgent | None = None
        best_matches = 0
        for agent in self.registry.list():
            matches = sum(
                keyword in normalized for keyword in agent.descriptor.keywords
            )
            if matches > best_matches:
                best_agent = agent
                best_matches = matches

        if best_agent is not None:
            return AgentRoute(
                agent=best_agent,
                reason=(
                    f"Agente {best_agent.descriptor.id} selecionado por "
                    f"{best_matches} correspondência(s) de intenção."
                ),
            )

        return AgentRoute(
            agent=self.registry.get(self.default_agent_id),
            reason="Nenhuma intenção especializada detectada; usando o agente geral.",
        )
