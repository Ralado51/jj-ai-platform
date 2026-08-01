from __future__ import annotations

from app.core.config import get_settings
from app.schemas.agents import AgentDescriptorResponse, AgentRunResponse
from app.services.agent_framework import (
    AgentDescriptor,
    AgentRegistry,
    AgentRouter,
    PromptAgent,
)
from app.services.chat_providers import OllamaChatProvider
from app.services.model_router import AITaskType, ModelRouter


class AgentService:
    def __init__(self, registry: AgentRegistry | None = None) -> None:
        self.registry = registry or self._build_registry()
        self.router = AgentRouter(self.registry)

    def list_agents(self) -> list[AgentDescriptorResponse]:
        return [
            AgentDescriptorResponse(
                id=agent.descriptor.id,
                name=agent.descriptor.name,
                description=agent.descriptor.description,
                task=agent.descriptor.task,
            )
            for agent in self.registry.list()
        ]

    def run(self, *, instruction: str, agent_id: str | None = None) -> AgentRunResponse:
        route = self.router.route(instruction=instruction, agent_id=agent_id)
        result = route.agent.execute(instruction=instruction)
        descriptor = result.agent
        return AgentRunResponse(
            agent=AgentDescriptorResponse(
                id=descriptor.id,
                name=descriptor.name,
                description=descriptor.description,
                task=descriptor.task,
            ),
            routing_reason=route.reason,
            content=result.content,
            provider=result.provider,
            model=result.model,
        )

    @staticmethod
    def _build_registry() -> AgentRegistry:
        settings = get_settings()
        model_router = ModelRouter(
            default_model=settings.ollama_chat_model,
            content_model=settings.ollama_content_model,
            rag_model=settings.ollama_rag_model,
            coding_model=settings.ollama_coding_model,
            summarization_model=settings.ollama_summarization_model,
            general_model=settings.ollama_general_model,
        )
        registry = AgentRegistry()

        definitions = (
            (
                AgentDescriptor(
                    id="content-creator",
                    name="Criador de Conteúdo",
                    description="Cria roteiros, posts, títulos, legendas e conteúdo para redes sociais.",
                    task=AITaskType.CONTENT_GENERATION,
                    keywords=("roteiro", "conteúdo", "post", "tiktok", "instagram", "linkedin", "legenda"),
                ),
                "Você é um estrategista de conteúdo. Entregue material prático, específico e pronto para uso.",
            ),
            (
                AgentDescriptor(
                    id="code-review",
                    name="Code Review",
                    description="Analisa, explica, corrige e melhora código.",
                    task=AITaskType.CODING,
                    keywords=("código", "codigo", "erro", "bug", "python", "javascript", "typescript", "sql", "refator"),
                ),
                "Você é um engenheiro de software sênior. Analise código com precisão, segurança e sugestões acionáveis.",
            ),
            (
                AgentDescriptor(
                    id="summarizer",
                    name="Resumo e Análise",
                    description="Resume materiais e extrai pontos principais, decisões e ações.",
                    task=AITaskType.SUMMARIZATION,
                    keywords=("resuma", "resumo", "sintetize", "principais pontos", "analise este texto"),
                ),
                "Você é um analista objetivo. Preserve fatos, destaque pontos principais e não invente informações.",
            ),
            (
                AgentDescriptor(
                    id="general",
                    name="Assistente Geral",
                    description="Atende solicitações gerais que não exigem um agente especializado.",
                    task=AITaskType.GENERAL,
                ),
                "Você é o assistente geral da JJ AI Platform. Responda com clareza, objetividade e precisão.",
            ),
        )

        for descriptor, system_prompt in definitions:
            route = model_router.route(descriptor.task)
            provider = OllamaChatProvider(
                base_url=settings.ollama_base_url,
                model=route.model,
                timeout_seconds=settings.ollama_chat_timeout_seconds,
                temperature=settings.ollama_chat_temperature,
                max_tokens=settings.ollama_chat_max_tokens,
                repeat_penalty=settings.ollama_chat_repeat_penalty,
                max_characters=settings.ollama_chat_max_characters,
            )
            registry.register(
                PromptAgent(
                    descriptor=descriptor,
                    provider=provider,
                    system_prompt=system_prompt,
                )
            )

        return registry
