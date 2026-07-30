from pathlib import Path


def test_rag_service_compiles() -> None:
    source_path = Path("app/services/rag_service.py")
    source = source_path.read_text(encoding="utf-8")
    compile(source, str(source_path), "exec")
