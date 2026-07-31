from __future__ import annotations

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.schemas.content_creator import (
    ContentCreatorBriefing,
    ContentCreatorResponse,
    ContentValidationResponse,
    PromptEvaluationResponse,
    PromptEvaluationScoresResponse,
)
from app.services.chat_providers import (
    ChatProvider,
    ChatProviderError,
    OllamaChatProvider,
)
from app.services.content_quality_pipeline import ContentQualityPipeline
from app.services.prompt_engine import PromptEngine


class ContentCreatorService:
    def __init__(self, *, provider: ChatProvider | None = None) -> None:
        settings = get_settings()
        self.provider = provider or OllamaChatProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_chat_model,
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
