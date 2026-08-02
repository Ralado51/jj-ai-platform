from __future__ import annotations

from time import perf_counter
from uuid import UUID

from app.core.config import get_settings
from app.repositories.agent_repository import AgentRepository
from app.repositories.benchmark_repository import BenchmarkRepository
from app.schemas.agents import AgentDescriptorResponse, AgentRunResponse
from app.schemas.search import RagAnswerRequest
from app.services.agent_framework import (
    AgentDescriptor,
    AgentRegistry,
    AgentRouter,
    PromptAgent,
)
from app.services.auto_model_rag_service import AutoModelRagService
from app.services.auto_model_selector import AutoModelSelector
from app.services.chat_providers import OllamaChatProvider
from app.services.model_router import AITaskType, ModelRouter


class AgentService:
    def __init__(
        self,
        registry: AgentRegistry | None = None,
        repository: AgentRepository | None = None,
        benchmark_repository: BenchmarkRepository | None = None,
        rag_service: AutoModelRagService | None = None,
        auto_selector: AutoModelSelector | None = None,
    ) -> None:
        self.settings = get_settings()
        self.model_router = ModelRouter(
            default_model=self.settings.ollama_chat_model,
            content_model=self.settings.ollama_content_model,
            rag_model=self.settings.ollama_rag_model,
            coding_model=self.settings.ollama_coding_model,
            summarization_model=self.settings.ollama_summarization_model,
            general_model=self.settings.ollama_general_model,
        )
        self.registry = registry or self._build_registry()
        self.router = AgentRouter(self.registry)
        self.repository = repository
        self.rag_service = rag_service
        self.auto_selector = auto_selector
        if self.auto_selector is None and benchmark_repository is not None:
            self.auto_selector = AutoModelSelector(
                repository=benchmark_repository,
                router=self.model_router,
                minimum_samples=self.settings.auto_model_minimum_samples,
                minimum_average_score=self.settings.auto_model_minimum_average_score,
            )

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

    def run(
        self,
        *,
        instruction: str,
        agent_id: str | None = None,
        user_id: UUID | None = None,
        project_id: UUID | None = None,
        session_key: str | None = None,
        use_memory: bool = True,
    ) -> AgentRunResponse:
        route = self.router.route(instruction=instruction, agent_id=agent_id)
        descriptor = route.agent.descriptor
        memory_items = []
        effective_instruction = instruction.strip()

        if (
            use_memory
            and self.repository is not None
            and user_id is not None
            and session_key
        ):
            memory_items = self.repository.recent_memory(
                user_id=user_id,
                agent_id=descriptor.id,
                session_key=session_key,
            )
            if memory_items:
                history = "\n".join(
                    f"{item.role.upper()}: {item.content}" for item in memory_items
                )
                effective_instruction = (
                    "HISTÓRICO RECENTE DESTA SESSÃO\n"
                    f"{history}\n\n"
                    "SOLICITAÇÃO ATUAL\n"
                    f"{instruction.strip()}\n\n"
                    "Use o histórico somente para continuidade. Priorize a solicitação atual."
                )

        started_at = perf_counter()
        routing_reason = route.reason
        selection_source = "configured_router"

        if descriptor.id == "rag":
            if project_id is None:
                raise ValueError("project_id is required for the RAG agent")
            if user_id is None or self.rag_service is None:
                raise ValueError("RAG agent runtime is not available")
            rag_result = self.rag_service.answer(
                project_id,
                user_id,
                RagAnswerRequest(question=effective_instruction),
            )
            content = rag_result.answer
            provider_name = rag_result.chat_provider
            model_name = rag_result.chat_model
            routing_reason = f"{route.reason} {rag_result.routing.reason}"
            selection_source = "rag_runtime"
        else:
            execution_agent = route.agent
            if (
                self.settings.auto_model_selection_enabled
                and self.auto_selector is not None
                and user_id is not None
                and isinstance(route.agent, PromptAgent)
            ):
                selection = self.auto_selector.select(
                    user_id=user_id,
                    task=descriptor.task,
                )
                execution_agent = PromptAgent(
                    descriptor=descriptor,
                    provider=self._build_provider(selection.model),
                    system_prompt=route.agent.system_prompt,
                )
                routing_reason = f"{route.reason} {selection.reason}"
                selection_source = selection.source

            result = execution_agent.execute(instruction=effective_instruction)
            content = result.content
            provider_name = result.provider
            model_name = result.model

        duration_ms = max(0, round((perf_counter() - started_at) * 1000))
        execution_id = None

        if self.repository is not None and user_id is not None:
            execution = self.repository.save_execution(
                user_id=user_id,
                agent_id=descriptor.id,
                task_type=descriptor.task.value,
                session_key=session_key,
                instruction=instruction.strip(),
                response=content,
                routing_reason=routing_reason,
                provider=provider_name,
                model=model_name,
                duration_ms=duration_ms,
            )
            execution_id = execution.id

        return AgentRunResponse(
            execution_id=execution_id,
            agent=AgentDescriptorResponse(
                id=descriptor.id,
                name=descriptor.name,
                description=descriptor.description,
                task=descriptor.task,
            ),
            routing_reason=routing_reason,
            content=content,
            provider=provider_name,
            model=model_name,
            model_selection_source=selection_source,
            duration_ms=duration_ms,
            memory_items_used=len(memory_items),
            session_key=session_key,
            project_id=project_id,
        )

    def _build_provider(self, model: str) -> OllamaChatProvider:
        return OllamaChatProvider(
            base_url=self.settings.ollama_base_url,
            model=model,
            timeout_seconds=self.settings.ollama_chat_timeout_seconds,
            temperature=self.settings.ollama_chat_temperature,
            max_tokens=self.settings.ollama_chat_max_tokens,
            repeat_penalty=self.settings.ollama_chat_repeat_penalty,
            max_characters=self.settings.ollama_chat_max_characters,
        )

    def _build_registry(self) -> AgentRegistry:
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
                    id="rag",
                    name="Conhecimento do Projeto",
                    description="Responde usando exclusivamente os documentos indexados de um projeto.",
                    task=AITaskType.RAG,
                    keywords=("documento", "pdf", "fonte", "contrato", "manual", "base de conhecimento", "projeto"),
                ),
                "Você responde exclusivamente com base nos documentos indexados do projeto.",
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
            model_route = self.model_router.route(descriptor.task)
            registry.register(
                PromptAgent(
                    descriptor=descriptor,
                    provider=self._build_provider(model_route.model),
                    system_prompt=system_prompt,
                )
            )

        return registry
