from __future__ import annotations

from dataclasses import dataclass

from app.services.chat_providers import ChatProvider
from app.services.content_output_validator import (
    ContentOutputValidator,
    ContentValidationResult,
)
from app.services.prompt_engine import PromptBuildResult


@dataclass(frozen=True)
class ContentRefinementResult:
    content: str
    validation: ContentValidationResult
    refined: bool


class ContentRefiner:
    """Validates generated content and performs at most one refinement attempt."""

    def __init__(
        self,
        *,
        provider: ChatProvider,
        validator: ContentOutputValidator | None = None,
    ) -> None:
        self.provider = provider
        self.validator = validator or ContentOutputValidator()

    def refine_once(
        self,
        *,
        original_content: str,
        original_prompt: PromptBuildResult,
    ) -> ContentRefinementResult:
        initial_validation = self.validator.validate(original_content)
        if initial_validation.is_valid:
            return ContentRefinementResult(
                content=original_content.strip(),
                validation=initial_validation,
                refined=False,
            )

        refinement_instructions = self.validator.build_refinement_instructions(
            initial_validation
        )
        user_prompt = (
            f"{original_prompt.user_prompt}\n\n"
            "RESPOSTA ORIGINAL\n"
            f"{original_content.strip()}\n\n"
            "INSTRUÇÕES DE REFINAMENTO\n"
            f"{refinement_instructions}\n\n"
            "Reescreva a resposta completa. Remova citações como [Fonte N], placeholders e "
            "observações sobre o processo. Mantenha apenas o conteúdo final pronto para uso."
        )
        refined_content = self.provider.generate(
            system_prompt=(
                f"{original_prompt.system_prompt} "
                "Você está revisando uma resposta já gerada. Preserve o briefing, corrija somente "
                "os problemas listados e não explique a revisão."
            ),
            user_prompt=user_prompt,
        ).strip()
        final_validation = self.validator.validate(refined_content)

        return ContentRefinementResult(
            content=refined_content,
            validation=final_validation,
            refined=True,
        )
