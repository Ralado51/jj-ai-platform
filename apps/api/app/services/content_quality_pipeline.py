from __future__ import annotations

from dataclasses import dataclass

from app.services.chat_providers import ChatProvider
from app.services.content_output_validator import (
    ContentOutputValidator,
    ContentValidationResult,
)
from app.services.content_refiner import ContentRefiner
from app.services.prompt_engine import PromptBuildResult
from app.services.prompt_evaluator import PromptEvaluationResult, PromptEvaluator


@dataclass(frozen=True)
class ContentQualityPipelineResult:
    content: str
    validation: ContentValidationResult
    evaluation: PromptEvaluationResult
    refined: bool


class ContentQualityPipeline:
    """Runs validator and evaluator before a single optional refinement pass."""

    def __init__(
        self,
        *,
        provider: ChatProvider,
        validator: ContentOutputValidator | None = None,
        evaluator: PromptEvaluator | None = None,
    ) -> None:
        self.provider = provider
        self.validator = validator or ContentOutputValidator()
        self.evaluator = evaluator or PromptEvaluator()
        self.refiner = ContentRefiner(provider=provider, validator=self.validator)

    def process(
        self,
        *,
        original_content: str,
        original_prompt: PromptBuildResult,
    ) -> ContentQualityPipelineResult:
        initial_validation = self.validator.validate(original_content)
        initial_evaluation = self.evaluator.evaluate(original_content)

        if initial_validation.is_valid and initial_evaluation.passed:
            return ContentQualityPipelineResult(
                content=original_content.strip(),
                validation=initial_validation,
                evaluation=initial_evaluation,
                refined=False,
            )

        refinement = self.refiner.refine_once(
            original_content=original_content,
            original_prompt=original_prompt,
        )
        final_evaluation = self.evaluator.evaluate(refinement.content)

        return ContentQualityPipelineResult(
            content=refinement.content,
            validation=refinement.validation,
            evaluation=final_evaluation,
            refined=refinement.refined,
        )
