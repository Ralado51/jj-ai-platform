from types import SimpleNamespace
from uuid import uuid4

from app.api.v1.routers import workflows
from app.events import version_subscribers
from app.events.types import WorkflowUpdated
from app.schemas.workflows import WorkflowUpdate


class FakeEventBus:
    def __init__(self) -> None:
        self.events = []

    def publish(self, event) -> None:
        self.events.append(event)


class FakeRepository:
    def save(self, workflow):
        return workflow


class _SessionContext:
    def __enter__(self):
        return object()

    def __exit__(self, exc_type, exc, traceback):
        return False


class _VersionRepository:
    created_values = None

    def __init__(self, db):
        self.db = db

    def create_once(self, *, values):
        type(self).created_values = values


def make_workflow():
    return SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        project_id=uuid4(),
        name="Research pipeline",
        description="Research and summarize",
        steps=[{"agent_id": "researcher", "instruction": "Research the topic"}],
        default_instruction="Analyze {{topic}}",
        session_key="research-session",
        use_memory=True,
        is_active=True,
    )


def test_workflow_snapshot_contains_executable_configuration() -> None:
    workflow = make_workflow()

    snapshot = workflows.workflow_snapshot(workflow)

    assert snapshot["name"] == "Research pipeline"
    assert snapshot["steps"] == [{"agent_id": "researcher", "instruction": "Research the topic"}]
    assert snapshot["default_instruction"] == "Analyze {{topic}}"
    assert snapshot["session_key"] == "research-session"
    assert snapshot["use_memory"] is True
    assert snapshot["is_active"] is True


def test_workflow_update_publishes_previous_and_current_snapshots(monkeypatch) -> None:
    event_bus = FakeEventBus()
    monkeypatch.setattr(workflows, "domain_event_bus", event_bus)
    workflow = make_workflow()
    user = SimpleNamespace(id=workflow.user_id)

    updated = workflows.apply_workflow_update(
        workflow=workflow,
        payload=WorkflowUpdate(
            name="Updated pipeline",
            steps=[{"agent_id": "writer", "instruction": "Write the report"}],
            use_memory=False,
        ),
        repository=FakeRepository(),
        user=user,
    )

    event = event_bus.events[-1]
    assert updated.name == "Updated pipeline"
    assert isinstance(event, WorkflowUpdated)
    assert event.previous_values["name"] == "Research pipeline"
    assert event.current_values["name"] == "Updated pipeline"
    assert event.current_values["steps"][0]["agent_id"] == "writer"
    assert event.current_values["use_memory"] is False


def test_workflow_event_is_stored_by_generic_version_engine(monkeypatch) -> None:
    _VersionRepository.created_values = None
    monkeypatch.setattr(version_subscribers, "SessionLocal", _SessionContext)
    monkeypatch.setattr(version_subscribers, "ResourceVersionRepository", _VersionRepository)
    workflow = make_workflow()
    event = WorkflowUpdated(
        actor_id=workflow.user_id,
        owner_id=workflow.user_id,
        project_id=workflow.project_id,
        workflow_id=workflow.id,
        previous_values={"name": "Before"},
        current_values=workflows.workflow_snapshot(workflow),
    )

    version_subscribers._record_workflow_version(event)

    values = _VersionRepository.created_values
    assert values["event_id"] == event.event_id
    assert values["resource_type"] == "workflow"
    assert values["resource_id"] == workflow.id
    assert values["snapshot"]["steps"][0]["agent_id"] == "researcher"
    assert len(values["checksum"]) == 64
