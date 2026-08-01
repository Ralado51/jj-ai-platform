from __future__ import annotations

from dataclasses import dataclass

from app.services.chat_providers import ChatProvider
from app.services.content_output_sanitizer import ContentOutputSanitizer
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
    """Runs validation, evaluation, optional refinement and final sanitization."""

    def __init__(
        self,
        *,
        provider: ChatProvider,
        validator: ContentOutputValidator | None = None,
        evaluator: PromptEvaluator | None = None,
        sanitizer: ContentOutputSanitizer | None = None,
    ) -> None:
        self.provider = provider
        self.validator = validator or ContentOutputValidator()
        self.evaluator = evaluator or PromptEvaluator()
        self.sanitizer = sanitizer or ContentOutputSanitizer()
        self.refiner = ContentRefiner(provider=provider, validator=self.validator)

    def process(
        self,
        *,
        original_content: str,
        original_prompt: PromptBuildResult,
    ) -> ContentQualityPipelineResult:
        initial_content = self.sanitizer.sanitize(original_content)
        initial_validation = self.validator.validate(initial_content)
        initial_evaluation = self.evaluator.evaluate(initial_content)

        if initial_validation.is_valid and initial_evaluation.passed:
            return ContentQualityPipelineResult(
                content=initial_content,
                validation=initial_validation,
                evaluation=initial_evaluation,
                refined=False,
            )

        refinement = self.refiner.refine_once(
            original_content=initial_content,
            original_prompt=original_prompt,
        )
        final_content = self.sanitizer.sanitize(refinement.content)
        final_validation = self.validator.validate(final_content)
        final_evaluation = self.evaluator.evaluate(final_content)

        return ContentQualityPipelineResult(
            content=final_content,
            validation=final_validation,
            evaluation=final_evaluation,
            refined=refinement.refined,
        )
