from types import SimpleNamespace
from uuid import uuid4

from app.schemas.prompt_evaluations import PromptEvaluationCreate
from app.services.prompt_evaluation_service import PromptEvaluationService


class FakeProvider:
    name = "test"
    model = "deterministic"

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        assert "JJ AI Platform" in system_prompt
        return "FastAPI with PostgreSQL and domain events"


class FakeRepository:
    def create(self, *, values):
        return SimpleNamespace(id=uuid4(), **values)


class FakeVersionRepository:
    def get(self, **kwargs):
        return None


class FakeEventBus:
    def __init__(self):
        self.events = []

    def publish(self, event):
        self.events.append(event)


def test_prompt_evaluation_runs_cases_and_publishes_event():
    repository = FakeRepository()
    event_bus = FakeEventBus()
    service = PromptEvaluationService(
        repository,
        FakeVersionRepository(),
        provider=FakeProvider(),
        event_bus=event_bus,
    )
    owner_id = uuid4()
    template = SimpleNamespace(
        id=uuid4(),
        owner_id=owner_id,
        project_id=uuid4(),
        content="You are evaluating {{product}}",
    )
    user = SimpleNamespace(id=owner_id, role="member")
    payload = PromptEvaluationCreate(
        name="Architecture regression",
        cases=[
            {
                "name": "platform stack",
                "input": "Describe the stack",
                "variables": {"product": "JJ AI Platform"},
                "expected_keywords": ["FastAPI", "PostgreSQL", "domain events"],
            }
        ],
    )

    evaluation = service.run(template=template, payload=payload, user=user)

    assert evaluation.status == "completed"
    assert evaluation.score == 1.0
    assert evaluation.results[0]["passed"] is True
    assert event_bus.events[0].evaluation_id == evaluation.id


def test_prompt_evaluation_scores_missing_keywords():
    score, matched, missing = PromptEvaluationService._score(
        output="FastAPI only",
        expected_output=None,
        expected_keywords=["FastAPI", "PostgreSQL"],
    )

    assert score == 0.5
    assert matched == ["FastAPI"]
    assert missing == ["PostgreSQL"]
