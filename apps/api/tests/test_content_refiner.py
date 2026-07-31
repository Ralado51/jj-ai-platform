from __future__ import annotations

from collections.abc import Iterator

from app.services.chat_providers import ChatProvider
from app.services.content_output_validator import ContentOutputValidator
from app.services.content_refiner import ContentRefiner
from app.services.prompt_engine import PromptBuildResult


class FakeProvider(ChatProvider):
    name = "fake"
    model = "fake-model"

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[tuple[str, str]] = []

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self.response

    def stream_generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> Iterator[str]:
        yield self.response


def _prompt() -> PromptBuildResult:
    return PromptBuildResult(
        system_prompt="Você é um roteirista.",
        user_prompt="Crie um roteiro de TikTok sobre guard-rails.",
    )


def _valid_content() -> str:
    return """### 1. Ideia central
Explicar guard-rails de forma simples.

### 2. Três opções de gancho
Gancho 1: Sua IA pode inventar regras sem você perceber.
Gancho 2: O que impede um chatbot de responder qualquer coisa?
Gancho 3: O freio de segurança que toda IA deveria ter.

### 3. Roteiro completo
0-5s: \"Sua IA pode inventar uma regra que nunca existiu.\"
6-13s: \"Por exemplo, um chatbot pode afirmar uma política falsa como se fosse oficial.\"
14-20s: \"Guard-rails bloqueiam esse comportamento antes que a resposta chegue ao usuário.\"

### 4. Três opções de título
Título 1: O freio de segurança da IA
Título 2: Como impedir respostas inventadas
Título 3: Por que toda IA precisa de limites

### 5. Legenda
Guard-rails ajudam a manter respostas dentro das regras definidas.

### 6. Hashtags
#GuardRails #IA #Seguranca

### 7. Chamada para ação
Quer aprender IA na prática? Inscreva-se.
"""


def test_refiner_skips_provider_when_content_is_valid() -> None:
    provider = FakeProvider(response="não deve ser usado")
    refiner = ContentRefiner(provider=provider)

    result = refiner.refine_once(
        original_content=_valid_content(),
        original_prompt=_prompt(),
    )

    assert result.refined is False
    assert result.validation.is_valid is True
    assert provider.calls == []


def test_refiner_calls_provider_once_for_invalid_content() -> None:
    provider = FakeProvider(response=_valid_content())
    refiner = ContentRefiner(provider=provider)

    result = refiner.refine_once(
        original_content="Roteiro: começar com uma explicação. [Fonte 1]",
        original_prompt=_prompt(),
    )

    assert result.refined is True
    assert result.validation.is_valid is True
    assert len(provider.calls) == 1
    assert "RESPOSTA ORIGINAL" in provider.calls[0][1]
    assert "INSTRUÇÕES DE REFINAMENTO" in provider.calls[0][1]
    assert "citações indevidas" in provider.calls[0][1]


def test_refiner_does_not_retry_when_refined_content_is_still_invalid() -> None:
    provider = FakeProvider(response="Ainda inválido [Fonte 1]")
    refiner = ContentRefiner(
        provider=provider,
        validator=ContentOutputValidator(),
    )

    result = refiner.refine_once(
        original_content="Começar com uma introdução. [Fonte 1]",
        original_prompt=_prompt(),
    )

    assert result.refined is True
    assert result.validation.is_valid is False
    assert len(provider.calls) == 1
