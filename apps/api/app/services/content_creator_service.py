from __future__ import annotations

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.schemas.content_creator import (
    ContentCreatorBriefing,
    ContentCreatorResponse,
    ContentValidationResponse,
    ModelRoutingResponse,
    PromptEvaluationResponse,
    PromptEvaluationScoresResponse,
)
from app.services.chat_providers import (
    ChatProvider,
    ChatProviderError,
    OllamaChatProvider,
)
from app.services.content_quality_pipeline import ContentQualityPipeline
from app.services.model_router import AITaskType, ModelRoute, ModelRouter
from app.services.prompt_engine import PromptEngine


class ContentCreatorService:
    def __init__(
        self,
        *,
        provider: ChatProvider | None = None,
        model_router: ModelRouter | None = None,
    ) -> None:
        settings = get_settings()

        if provider is not None:
            self.route = ModelRoute(
                task=AITaskType.CONTENT_GENERATION,
                model=provider.model,
                reason="Provider injetado diretamente no Content Creator.",
                used_fallback=False,
            )
            self.provider = provider
        else:
            router = model_router or ModelRouter(
                default_model=settings.ollama_chat_model,
                content_model=settings.ollama_content_model,
                rag_model=settings.ollama_rag_model,
                coding_model=settings.ollama_coding_model,
                summarization_model=settings.ollama_summarization_model,
                general_model=settings.ollama_general_model,
            )
            self.route = router.route(AITaskType.CONTENT_GENERATION)
            self.provider = OllamaChatProvider(
                base_url=settings.ollama_base_url,
                model=self.route.model,
                timeout_seconds=settings.ollama_chat_timeout_seconds,
                temperature=settings.ollama_chat_temperature,
            )

        self.prompt_engine = PromptEngine()
        self.pipeline = ContentQualityPipeline(provider=self.provider)

    def generate(self, briefing: ContentCreatorBriefing) -> ContentCreatorResponse:
        prompt = self.prompt_engine.build_content_creator_prompt(
            briefing=briefing.model_dump()
        )

        try:
            original_content = self.provider.generate(
                system_prompt=prompt.system_prompt,
                user_prompt=prompt.user_prompt,
            )
            result = self.pipeline.process(
                original_content=original_content,
                original_prompt=prompt,
            )
        except (httpx.HTTPError, ChatProviderError) as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Não foi possível gerar o conteúdo com o modelo local.",
            ) from exc

        scores = result.evaluation.scores
        return ContentCreatorResponse(
            content=result.content,
            provider=self.provider.name,
            model=self.provider.model,
            routing=ModelRoutingResponse(
                task=self.route.task.value,
                model=self.route.model,
                reason=self.route.reason,
                used_fallback=self.route.used_fallback,
            ),
            refined=result.refined,
            validation=ContentValidationResponse(
                is_valid=result.validation.is_valid,
                issues=list(result.validation.issues),
            ),
            evaluation=PromptEvaluationResponse(
                scores=PromptEvaluationScoresResponse(
                    hook=scores.hook,
                    storytelling=scores.storytelling,
                    clarity=scores.clarity,
                    originality=scores.originality,
                    call_to_action=scores.call_to_action,
                    structure=scores.structure,
                    overall=scores.overall,
                ),
                issues=list(result.evaluation.issues),
                strengths=list(result.evaluation.strengths),
                passed=result.evaluation.passed,
            ),
        )
