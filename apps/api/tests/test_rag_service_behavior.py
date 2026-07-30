from app.services.rag_service import RagService


def test_build_snippet_normalizes_whitespace() -> None:
    assert RagService._build_snippet("texto\n  com   espaços") == "texto com espaços"


def test_normalize_inline_citations_appends_fallback() -> None:
    assert RagService._normalize_inline_citations("Resposta", 1) == "Resposta [Fonte 1]"
