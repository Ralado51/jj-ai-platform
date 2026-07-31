import pytest

from app.services.prompt_engine import PromptEngine


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
