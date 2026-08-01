from types import SimpleNamespace
from uuid import uuid4

from app.schemas.search import RagAnswerRequest
from app.services.auto_model_rag_service import AutoModelRagService
from app.services.model_router import AITaskType
from app.services.rag_service import RagService


class FakeSelector:
    def __init__(self) -> None:
        self.calls = []

    def select(self, *, user_id, task):
        self.calls.append((user_id, task))
        return SimpleNamespace(
            task=task,
            model="winner:latest",
            reason="Selected from benchmark history.",
            used_fallback=False,
        )


def build_service(*, enabled: bool, selector: FakeSelector) -> AutoModelRagService:
    service = AutoModelRagService.__new__(AutoModelRagService)
    service.auto_model_selection_enabled = enabled
    service.auto_selector = selector
    service.settings = SimpleNamespace(
        ollama_base_url="http://ollama:11434",
        ollama_chat_timeout_seconds=180.0,
        ollama_chat_temperature=0.2,
    )
    return service


def test_rag_uses_history_selected_model(monkeypatch) -> None:
    original = {
        "route": SimpleNamespace(model="configured:latest"),
        "provider": SimpleNamespace(model="configured:latest"),
    }
    monkeypatch.setattr(
        RagService,
        "_prepare_answer",
        lambda self, project_id, user_id, data: dict(original),
    )
    selector = FakeSelector()
    service = build_service(enabled=True, selector=selector)
    user_id = uuid4()

    prepared = service._prepare_answer(
        uuid4(),
        user_id,
        RagAnswerRequest(question="Explique o documento."),
    )

    assert prepared["route"].model == "winner:latest"
    assert prepared["provider"].model == "winner:latest"
    assert selector.calls == [(user_id, AITaskType.RAG)]


def test_rag_keeps_configured_route_when_auto_selection_is_disabled(monkeypatch) -> None:
    original = {
        "route": SimpleNamespace(model="configured:latest"),
        "provider": SimpleNamespace(model="configured:latest"),
    }
    monkeypatch.setattr(
        RagService,
        "_prepare_answer",
        lambda self, project_id, user_id, data: dict(original),
    )
    selector = FakeSelector()
    service = build_service(enabled=False, selector=selector)

    prepared = service._prepare_answer(
        uuid4(),
        uuid4(),
        RagAnswerRequest(question="Explique o documento."),
    )

    assert prepared["route"].model == "configured:latest"
    assert prepared["provider"].model == "configured:latest"
    assert selector.calls == []
