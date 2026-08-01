from __future__ import annotations

from uuid import UUID

from app.core.config import get_settings
from app.repositories.asset_repository import AssetRepository
from app.repositories.benchmark_repository import BenchmarkRepository
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.search import RagAnswerRequest
from app.services.auto_model_selector import AutoModelSelector
from app.services.chat_providers import OllamaChatProvider
from app.services.model_router import AITaskType, ModelRouter
from app.services.rag_service import RagService
from app.services.search_service import SemanticSearchService


class AutoModelRagService(RagService):
    """RAG runtime that selects one model from benchmark history when enabled."""

    def __init__(
        self,
        *,
        search_service: SemanticSearchService,
        asset_repository: AssetRepository,
        conversation_repository: ConversationRepository,
        benchmark_repository: BenchmarkRepository,
        auto_selector: AutoModelSelector | None = None,
    ) -> None:
        super().__init__(
            search_service=search_service,
            asset_repository=asset_repository,
            conversation_repository=conversation_repository,
        )
        settings = get_settings()
        self.auto_model_selection_enabled = settings.auto_model_selection_enabled
        self.auto_selector = auto_selector or AutoModelSelector(
            repository=benchmark_repository,
            router=ModelRouter(
                default_model=settings.ollama_chat_model,
                content_model=settings.ollama_content_model,
                rag_model=settings.ollama_rag_model,
                coding_model=settings.ollama_coding_model,
                summarization_model=settings.ollama_summarization_model,
                general_model=settings.ollama_general_model,
            ),
            minimum_samples=settings.auto_model_minimum_samples,
            minimum_average_score=settings.auto_model_minimum_average_score,
        )

    def _prepare_answer(
        self,
        project_id: UUID,
        user_id: UUID,
        data: RagAnswerRequest,
    ) -> dict:
        prepared = super()._prepare_answer(project_id, user_id, data)
        if not self.auto_model_selection_enabled:
            return prepared

        selection = self.auto_selector.select(
            user_id=user_id,
            task=AITaskType.RAG,
        )
        prepared["route"] = selection
        prepared["provider"] = OllamaChatProvider(
            base_url=self.settings.ollama_base_url,
            model=selection.model,
            timeout_seconds=self.settings.ollama_chat_timeout_seconds,
            temperature=self.settings.ollama_chat_temperature,
        )
        return prepared
