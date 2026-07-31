from __future__ import annotations

from collections.abc import Iterator

from app.services.chat_providers import ChatProvider
from app.services.content_quality_pipeline import ContentQualityPipeline
from app.services.prompt_engine import PromptBuildResult


class FakeProvider(ChatProvider):
    name = "fake"
    model = "fake-model"

    def __init__(self, refined_content: str) -> None:
        self.refined_content = refined_content
        self.calls = 0

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        self.calls += 1
        return self.refined_content

    def stream_generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> Iterator[str]:
        yield self.refined_content


def build_prompt() -> PromptBuildResult:
    return PromptBuildResult(
        system_prompt="Você cria conteúdo pronto para publicação.",
        user_prompt="Crie um roteiro completo sobre guard-rails em IA.",
    )


def strong_content() -> str:
    return """
### 1. Ideia Central Clara
Explicar como guard-rails evitam respostas perigosas em sistemas de IA.

### 2. Opções de Gancho
Gancho 1: "Sua IA pode inventar uma regra agora mesmo."
Gancho 2: "Como impedir um chatbot de prejudicar sua empresa?"
Gancho 3: "O erro invisível que transforma IA em risco."

### 3. Roteiro Completo
0-4s: "Sua IA pode inventar uma política que nunca existiu."
5-10s: "Problema: sem limites, o chatbot responde qualquer coisa."
11-16s: "Consequência: a empresa pode perder dinheiro e confiança."
17-22s: "Solução: guard-rails bloqueiam instruções perigosas e exigem respostas verificáveis."
23-27s: "Por exemplo, um filtro pode impedir a IA de aprovar reembolsos fora da política."

### 4. Títulos
Título 1: "Sua IA está inventando regras?"
Título 2: "O freio de segurança que todo chatbot precisa"
Título 3: "Como proteger sua empresa de respostas perigosas"

### 5. Legenda
Guard-rails funcionam como freios de segurança para sistemas de IA.

### 6. Hashtags Relevantes
#InteligenciaArtificial #Guardrails #SegurancaDigital

### 7. Chamada para Ação Final
Comente "guard-rails" para receber mais exemplos práticos.
"""


def test_returns_without_refinement_when_quality_passes() -> None:
    provider = FakeProvider(strong_content())
    pipeline = ContentQualityPipeline(provider=provider)

    result = pipeline.process(
        original_content=strong_content(),
        original_prompt=build_prompt(),
    )

    assert result.refined is False
    assert result.validation.is_valid is True
    assert result.evaluation.passed is True
    assert provider.calls == 0


def test_refines_once_when_validation_or_evaluation_fails() -> None:
    provider = FakeProvider(strong_content())
    pipeline = ContentQualityPipeline(provider=provider)

    result = pipeline.process(
        original_content="### Ideia Central\nComeçar com uma explicação. [Fonte 1]",
        original_prompt=build_prompt(),
    )

    assert result.refined is True
    assert result.validation.is_valid is True
    assert result.evaluation.passed is True
    assert provider.calls == 1


def test_never_refines_more_than_once() -> None:
    provider = FakeProvider("Resposta ainda incompleta [Fonte 1]")
    pipeline = ContentQualityPipeline(provider=provider)

    result = pipeline.process(
        original_content="Resposta inválida [Fonte 1]",
        original_prompt=build_prompt(),
    )

    assert result.refined is True
    assert result.validation.is_valid is False
    assert result.evaluation.passed is False
    assert provider.calls == 1
