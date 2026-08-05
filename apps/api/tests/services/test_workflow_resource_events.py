from uuid import uuid4

from app.events import resource_subscribers
from app.events.types import WorkflowArchived, WorkflowCreated


class _SessionContext:
    def __enter__(self):
        return object()

    def __exit__(self, exc_type, exc, traceback):
        return False


class _ResourceRepository:
    values = None

    def __init__(self, db):
        self.db = db

    def find_registered(self, **kwargs):
        return None

    def create(self, *, owner_id, values):
        type(self).values = {"owner_id": owner_id, **values}


def _snapshot(*, active: bool, steps: list[dict], use_memory: bool) -> dict:
    return {
        "name": "Content pipeline",
        "description": "Creates and reviews content",
        "project_id": None,
        "steps": steps,
        "default_instruction": None,
        "session_key": None,
        "use_memory": use_memory,
        "is_active": active,
    }


def test_workflow_created_registers_active_resource(monkeypatch):
    _ResourceRepository.values = None
    monkeypatch.setattr(resource_subscribers, "SessionLocal", _SessionContext)
    monkeypatch.setattr(resource_subscribers, "ResourceRegistryRepository", _ResourceRepository)
    owner_id = uuid4()
    project_id = uuid4()
    event = WorkflowCreated(
        actor_id=owner_id,
        owner_id=owner_id,
        project_id=project_id,
        workflow_id=uuid4(),
        current_values=_snapshot(
            active=True,
            steps=[{"agent_id": "content-creator"}, {"agent_id": "code-review"}],
            use_memory=True,
        ),
    )

    resource_subscribers._upsert_workflow_resource(event)

    values = _ResourceRepository.values
    assert values["owner_id"] == owner_id
    assert values["resource_type"] == "workflow"
    assert values["resource_id"] == event.workflow_id
    assert values["project_id"] == project_id
    assert values["status"] == "active"
    assert values["resource_metadata"] == {"steps_count": 2, "use_memory": True}


def test_workflow_archived_registers_archived_status(monkeypatch):
    _ResourceRepository.values = None
    monkeypatch.setattr(resource_subscribers, "SessionLocal", _SessionContext)
    monkeypatch.setattr(resource_subscribers, "ResourceRegistryRepository", _ResourceRepository)
    owner_id = uuid4()
    event = WorkflowArchived(
        actor_id=owner_id,
        owner_id=owner_id,
        project_id=None,
        workflow_id=uuid4(),
        current_values=_snapshot(active=False, steps=[], use_memory=False),
    )

    resource_subscribers._upsert_workflow_resource(event)

    values = _ResourceRepository.values
    assert values["status"] == "archived"
    assert values["project_id"] is None
