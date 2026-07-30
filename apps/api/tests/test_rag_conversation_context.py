from app.services.rag_service import RagService


def test_build_prompts_includes_recent_conversation_history() -> None:
    _, user_prompt = RagService._build_prompts(
        "[Fonte 1] conteúdo",
        "E a cláusula 5?",
        "Usuário: Explique o contrato.\nAssistente: O contrato define...",
    )

    assert "HISTÓRICO RECENTE DA CONVERSA" in user_prompt
    assert "Usuário: Explique o contrato." in user_prompt
    assert "PERGUNTA DO USUÁRIO\nE a cláusula 5?" in user_prompt


def test_build_prompts_omits_empty_history_block() -> None:
    _, user_prompt = RagService._build_prompts(
        "[Fonte 1] conteúdo",
        "Explique o contrato.",
    )

    assert "HISTÓRICO RECENTE DA CONVERSA" not in user_prompt
