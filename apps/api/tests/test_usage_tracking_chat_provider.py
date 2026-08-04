from uuid import uuid4

from app.services.chat_providers import ChatProvider
from app.services.usage_tracking_chat_provider import UsageTrackingChatProvider


class _Provider(ChatProvider):
    name = "ollama"
    model = "gemma3:4b"

    def __init__(self) -> None:
        self.last_usage = {"prompt_tokens": 12, "completion_tokens": 7}

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        return "resposta"

    def stream_generate(self, *, system_prompt: str, user_prompt: str):
        yield "res"
        yield "posta"


class _Repository:
    def __init__(self) -> None:
        self.measurements = []

    def create(self, **kwargs):
        self.measurements.append(kwargs)
        return kwargs


def test_tracks_exact_provider_usage() -> None:
    repository = _Repository()
    tracked = UsageTrackingChatProvider(
        provider=_Provider(),
        repository=repository,
        user_id=uuid4(),
        project_id=uuid4(),
        task="content_generation",
    )

    assert tracked.generate(system_prompt="sistema", user_prompt="usuario") == "resposta"
    assert len(repository.measurements) == 1
    measurement = repository.measurements[0]["measurement"]
    assert measurement.prompt_tokens == 12
    assert measurement.completion_tokens == 7
    assert measurement.provider == "ollama"
    assert measurement.model == "gemma3:4b"


def test_tracks_stream_after_completion() -> None:
    repository = _Repository()
    tracked = UsageTrackingChatProvider(
        provider=_Provider(),
        repository=repository,
        user_id=uuid4(),
    )

    assert "".join(tracked.stream_generate(system_prompt="s", user_prompt="u")) == "resposta"
    assert len(repository.measurements) == 1
