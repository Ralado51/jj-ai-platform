from __future__ import annotations

from collections.abc import Iterator

from app.schemas.content_creator import ContentCreatorBriefing
from app.services.chat_providers import ChatProvider
from app.services.content_creator_service import ContentCreatorService


class FakeProvider(ChatProvider):
    name = "fake"
    model = "fake-model"

    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls = 0

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return response

    def stream_generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> Iterator[str]:
        yield self.generate(system_prompt=system_prompt, user_prompt=user_prompt)


def briefing() -> ContentCreatorBriefing:
    return ContentCreatorBriefing(
        tema="Como guard-rails ajudam na IA",
        publico="Profissionais de TI",
        plataforma="TikTok",
        objetivo="Ganhar inscritos",
        formato="Vídeo curto",
        tom="Descontraído",
        duracao="20 segundos",
        cta="Inscreva-se",
    )


def strong_content() -> str:
    return """
### 1. Ideia Central
Explicar como guard-rails evitam respostas perigosas em sistemas de IA.

### 2. Opções de Gancho
Gancho 1: "Sua IA pode inventar uma regra agora mesmo."
Gancho 2: "Como impedir um chatbot de prejudicar sua empresa?"
Gancho 3: "O erro invisível que transforma IA em risco."

### 3. Roteiro Completo
0-4s: "Sua IA pode inventar uma política que nunca existiu."
5-9s: "Problema: sem limites, o chatbot responde qualquer coisa."
10-14s: "Por exemplo, ele pode aprovar um reembolso inexistente."
15-18s: "Consequência: prejuízo e perda de confiança."
19-20s: "Solução: guard-rails bloqueiam respostas inseguras."

### 4. Títulos
Título 1: "Sua IA está inventando regras?"
Título 2: "O freio de segurança que todo chatbot precisa"
Título 3: "Como proteger sua empresa de respostas perigosas"

### 5. Legenda
Guard-rails funcionam como freios de segurança para sistemas de IA.

### 6. Hashtags Relevantes
#InteligenciaArtificial #Guardrails #SegurancaDigital

### 7. Chamada para Ação Final
Inscreva-se para ver mais exemplos práticos.
"""


def test_generate_returns_quality_metadata_without_refinement() -> None:
    provider = FakeProvider([strong_content()])
    service = ContentCreatorService(provider=provider)

    result = service.generate(briefing())

    assert result.provider == "fake"
    assert result.model == "fake-model"
    assert result.refined is False
    assert result.validation.is_valid is True
    assert result.evaluation.passed is True
    assert result.evaluation.scores.overall >= 8.0
    assert provider.calls == 1


def test_generate_refines_once_when_initial_content_fails() -> None:
    provider = FakeProvider(
        [
            "Ideia central: começar com uma explicação. [Fonte 1]",
            strong_content(),
        ]
    )
    service = ContentCreatorService(provider=provider)

    result = service.generate(briefing())

    assert result.refined is True
    assert result.validation.is_valid is True
    assert result.evaluation.passed is True
    assert provider.calls == 2
