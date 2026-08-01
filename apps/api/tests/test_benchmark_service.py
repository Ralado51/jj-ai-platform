from __future__ import annotations

from app.schemas.benchmark import BenchmarkRunRequest
from app.services import benchmark_service as benchmark_module
from app.services.benchmark_service import BenchmarkService


class FakeProvider:
    name = "ollama"

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float,
        temperature: float,
    ) -> None:
        del base_url, timeout_seconds, temperature
        self.model = model

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        del system_prompt, user_prompt
        if self.model == "broken-model":
            raise benchmark_module.ChatProviderError("model unavailable")
        if self.model == "strong-model":
            return """
### Ideia Central
Explicar um risco real de IA.
### Opções de Gancho
Gancho 1: Como uma IA pode inventar regras?
Gancho 2: O erro que transforma chatbot em risco
Gancho 3: Por que seu modelo precisa de limites?
### Roteiro Completo
0-5s: Problema: a IA responde fora da política.
6-10s: Por exemplo, ela pode aprovar algo inexistente.
11-15s: Consequência: prejuízo e perda de confiança.
16-20s: Solução: guard-rails bloqueiam respostas inseguras.
### Títulos
Título 1: O freio de segurança da IA
Título 2: Como proteger um chatbot
Título 3: Limites para modelos seguros
### Legenda
Guard-rails reduzem riscos em sistemas de IA.
### Hashtags
#IA #Guardrails
### Chamada para Ação
Siga para ver mais exemplos.
"""
        return "Resposta curta e sem estrutura."


def test_benchmark_ranks_successful_models(monkeypatch) -> None:
    monkeypatch.setattr(benchmark_module, "OllamaChatProvider", FakeProvider)
    service = BenchmarkService()

    result = service.run(
        BenchmarkRunRequest(
            prompt="Crie um roteiro sobre guard-rails.",
            models=["weak-model", "strong-model"],
        )
    )

    assert result.winner == "strong-model"
    assert result.results[0].model == "strong-model"
    assert result.results[0].success is True
    assert result.results[0].scores is not None
    assert result.results[0].scores.overall > result.results[1].scores.overall


def test_benchmark_keeps_failed_models_without_interrupting(monkeypatch) -> None:
    monkeypatch.setattr(benchmark_module, "OllamaChatProvider", FakeProvider)
    service = BenchmarkService()

    result = service.run(
        BenchmarkRunRequest(
            prompt="Analise este conteúdo.",
            models=["strong-model", "broken-model"],
        )
    )

    failed = next(item for item in result.results if item.model == "broken-model")
    assert result.winner == "strong-model"
    assert failed.success is False
    assert failed.error == "model unavailable"
    assert failed.scores is None


def test_benchmark_requires_two_distinct_models() -> None:
    service = BenchmarkService()

    try:
        service.run(
            BenchmarkRunRequest(
                prompt="Analise este conteúdo.",
                models=["qwen2.5:3b", "qwen2.5:3b"],
            )
        )
    except ValueError as exc:
        assert "two distinct models" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
