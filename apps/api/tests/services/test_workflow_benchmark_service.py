from types import SimpleNamespace
from uuid import uuid4

from app.schemas.workflow_benchmarks import WorkflowBenchmarkCreate
from app.services.workflow_benchmark_service import WorkflowBenchmarkService


class FakeRepository:
    def create(self, *, values):
        return SimpleNamespace(id=uuid4(), **values)


class FakeVersionRepository:
    def get(self, *, version_number, **kwargs):
        return SimpleNamespace(
            snapshot={
                "steps": [
                    {
                        "agent_id": "writer" if version_number == 1 else "reviewer",
                        "instruction": "Answer clearly",
                    }
                ]
            }
        )


class FakeAgentService:
    def run(self, *, agent_id, **kwargs):
        content = (
            "FastAPI"
            if agent_id == "writer"
            else "FastAPI with PostgreSQL and domain events"
        )
        return SimpleNamespace(
            content=content,
            duration_ms=10,
            execution_id=uuid4(),
            agent=SimpleNamespace(
                id=agent_id,
                name=agent_id,
                task=SimpleNamespace(value="general"),
            ),
            provider="test",
            model="deterministic",
            model_selection_source="test",
            routing_reason="benchmark",
            memory_items_used=0,
        )


class FakeEventBus:
    def __init__(self):
        self.events = []

    def publish(self, event):
        self.events.append(event)


def test_workflow_benchmark_compares_versions_and_publishes_event():
    repository = FakeRepository()
    event_bus = FakeEventBus()
    service = WorkflowBenchmarkService(
        repository,
        FakeVersionRepository(),
        agent_service=FakeAgentService(),
        event_bus=event_bus,
    )
    owner_id = uuid4()
    workflow = SimpleNamespace(
        id=uuid4(),
        user_id=owner_id,
        project_id=uuid4(),
    )
    user = SimpleNamespace(id=owner_id, role="member")
    payload = WorkflowBenchmarkCreate(
        name="Workflow regression",
        versions=[1, 2],
        cases=[
            {
                "name": "architecture",
                "input": "Describe the stack",
                "expected_keywords": [
                    "FastAPI",
                    "PostgreSQL",
                    "domain events",
                ],
            }
        ],
    )

    benchmark = service.run(workflow=workflow, payload=payload, user=user)

    assert benchmark.status == "completed"
    assert benchmark.winner_version == 2
    assert benchmark.results[0]["version"] == 2
    assert benchmark.results[0]["score"] == 1.0
    assert event_bus.events[0].benchmark_id == benchmark.id


def test_workflow_benchmark_requires_distinct_versions():
    try:
        WorkflowBenchmarkCreate(
            name="Invalid",
            versions=[1, 1],
            cases=[
                {
                    "name": "case",
                    "input": "input",
                    "expected_keywords": ["answer"],
                }
            ],
        )
    except ValueError as exc:
        assert "versions must be distinct" in str(exc)
    else:
        raise AssertionError("duplicate versions should fail validation")
