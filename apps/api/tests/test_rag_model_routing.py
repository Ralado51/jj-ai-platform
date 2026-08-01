from app.services.model_router import AITaskType, ModelRouter


def test_rag_route_uses_configured_model() -> None:
    router = ModelRouter(
        default_model="qwen2.5:3b",
        rag_model="qwen2.5:7b",
    )

    route = router.route(AITaskType.RAG)

    assert route.task is AITaskType.RAG
    assert route.model == "qwen2.5:7b"
    assert route.used_fallback is False


def test_rag_route_falls_back_to_default_model() -> None:
    router = ModelRouter(default_model="qwen2.5:3b", rag_model="")

    route = router.route(AITaskType.RAG)

    assert route.task is AITaskType.RAG
    assert route.model == "qwen2.5:3b"
    assert route.used_fallback is True
