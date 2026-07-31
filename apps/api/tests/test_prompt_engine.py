import pytest

from app.services.prompt_engine import PromptEngine, PromptOptimizer


def test_build_rag_prompt_preserves_context_and_history() -> None:
    engine = PromptEngine()

    result = engine.build_rag_prompt(
        context="[Fonte 1] Guard-rails limitam comportamentos.",
        question="Como funcionam?",
        conversation_history="Usuário: O que são guard-rails?",
    )

    assert "CONTEXTO DE REFERÊNCIA" in result.user_prompt
    assert "HISTÓRICO RECENTE DA CONVERSA" in result.user_prompt
    assert "Como funcionam?" in result.user_prompt
    assert "[Fonte N]" in result.system_prompt


def test_build_content_creator_prompt_adds_duration_and_platform_rules() -> None:
    engine = PromptEngine()

    result = engine.build_content_creator_prompt(
        briefing={
            "tema": "Como guard-rails ajudam na IA",
            "publico": "Profissionais de TI",
            "plataforma": "TikTok",
            "objetivo": "Ganhar inscritos",
            "formato": "Vídeo curto",
            "tom": "Descontraído",
            "duracao": "20 segundos",
            "cta": "Inscreva-se",
        }
    )

    assert "Duração máxima: 20 segundos" in result.user_prompt
    assert "O roteiro completo deve caber" in result.user_prompt
    assert "primeiros 2 segundos" in result.user_prompt
    assert "TikTok" in result.user_prompt
    assert "roteirista especialista" in result.system_prompt


def test_content_prompt_is_optimized_for_retention_and_concrete_examples() -> None:
    engine = PromptEngine()

    result = engine.build_content_creator_prompt(
        briefing={
            "tema": "Como guard-rails ajudam na IA",
            "publico": "Profissionais de TI",
            "plataforma": "TikTok",
            "objetivo": "Ganhar inscritos",
            "formato": "Vídeo curto",
            "tom": "Descontraído",
            "duracao": "20 segundos",
            "cta": "Inscreva-se",
        }
    )

    assert "REGRAS DE OTIMIZAÇÃO" in result.user_prompt
    assert "provoque curiosidade" in result.user_prompt
    assert "exemplo concreto" in result.user_prompt
    assert "gancho, explicação, exemplo e CTA" in result.user_prompt
    assert "maximizar retenção" in result.system_prompt


def test_prompt_optimizer_can_be_injected() -> None:
    class StubOptimizer(PromptOptimizer):
        def optimize_content_prompt(self, prompt):
            return type(prompt)(
                system_prompt=f"{prompt.system_prompt} TESTE",
                user_prompt=f"{prompt.user_prompt} TESTE",
            )

    engine = PromptEngine(optimizer=StubOptimizer())
    result = engine.build_content_creator_prompt(
        briefing={
            "tema": "Guard-rails",
            "publico": "Profissionais de TI",
            "plataforma": "TikTok",
            "objetivo": "Ganhar inscritos",
            "formato": "Vídeo curto",
            "tom": "Descontraído",
            "duracao": "20 segundos",
            "cta": "Inscreva-se",
        }
    )

    assert result.system_prompt.endswith("TESTE")
    assert result.user_prompt.endswith("TESTE")


def test_build_content_creator_prompt_rejects_incomplete_briefing() -> None:
    engine = PromptEngine()

    with pytest.raises(ValueError) as exc_info:
        engine.build_content_creator_prompt(
            briefing={
                "tema": "Guard-rails",
                "publico": "Profissionais de TI",
            }
        )

    assert "Campos obrigatórios ausentes" in str(exc_info.value)
    assert "plataforma" in str(exc_info.value)
