from types import SimpleNamespace
from uuid import uuid4

from app.schemas.playground import PlaygroundRunCreate
from app.services.playground_service import PlaygroundService


class FakeRepository:
    def create_run(self, *, values):
        return SimpleNamespace(id=uuid4(), **values)


class FakeAgentService:
    def run(self, *, instruction, agent_id, **kwargs):
        return SimpleNamespace(
            content=f"answer:{instruction}",
            provider="test",
            model="deterministic",
            duration_ms=12,
            model_dump=lambda **kwargs: {
                "content": f"answer:{instruction}",
                "provider": "test",
                "model": "deterministic",
            },
        )


class FakeEventBus:
    def __init__(self):
        self.events = []

    def publish(self, event):
        self.events.append(event)


def test_playground_runs_agent_without_memory_and_publishes_event():
    event_bus = FakeEventBus()
    service = PlaygroundService(
        FakeRepository(),
        agent_service=FakeAgentService(),
        event_bus=event_bus,
    )
    owner_id = uuid4()
    session = SimpleNamespace(id=uuid4(), project_id=uuid4())
    result = service.run(
        session=session,
        payload=PlaygroundRunCreate(
            mode="agent", agent_id="general", input="hello"
        ),
        owner_id=owner_id,
    )

    assert result.status == "completed"
    assert result.output == "answer:hello"
    assert result.provider == "test"
    assert event_bus.events[0].run_id == result.id
    assert event_bus.events[0].status == "completed"


def test_playground_persists_failed_runs():
    class FailingAgentService:
        def run(self, **kwargs):
            raise RuntimeError("provider unavailable")

    service = PlaygroundService(
        FakeRepository(),
        agent_service=FailingAgentService(),
        event_bus=FakeEventBus(),
    )
    result = service.run(
        session=SimpleNamespace(id=uuid4(), project_id=None),
        payload=PlaygroundRunCreate(input="hello"),
        owner_id=uuid4(),
    )

    assert result.status == "failed"
    assert result.output == ""
    assert result.error == "provider unavailable"


def test_orchestration_requires_steps():
    try:
        PlaygroundRunCreate(mode="orchestration", input="hello")
    except ValueError as exc:
        assert "requires at least one step" in str(exc)
    else:
        raise AssertionError("orchestration without steps should fail")
