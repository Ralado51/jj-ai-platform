from types import SimpleNamespace
from uuid import uuid4

from app.api.v1.routers import workflows
from app.events.bus import DomainEventBus
from app.events.resource_events import ResourceUpserted


def test_publish_workflow_resource_emits_active_workflow(monkeypatch):
    owner_id = uuid4()
    project_id = uuid4()
    workflow = SimpleNamespace(
        id=uuid4(),
        user_id=owner_id,
        project_id=project_id,
        name="Content pipeline",
        description="Creates and reviews content",
        is_active=True,
        steps=[{"agent_id": "content-creator"}, {"agent_id": "code-review"}],
        use_memory=True,
    )
    events = []
    bus = DomainEventBus(strict=True)
    bus.subscribe(ResourceUpserted, events.append)
    monkeypatch.setattr(workflows, "domain_event_bus", bus)

    workflows.publish_workflow_resource(workflow)

    assert len(events) == 1
    assert events[0].owner_id == owner_id
    assert events[0].resource_type == "workflow"
    assert events[0].resource_id == workflow.id
    assert events[0].project_id == project_id
    assert events[0].status == "active"
    assert events[0].metadata == {"steps_count": 2, "use_memory": True}


def test_publish_workflow_resource_emits_archived_status(monkeypatch):
    workflow = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        project_id=None,
        name="Archived workflow",
        description=None,
        is_active=False,
        steps=[],
        use_memory=False,
    )
    events = []
    bus = DomainEventBus(strict=True)
    bus.subscribe(ResourceUpserted, events.append)
    monkeypatch.setattr(workflows, "domain_event_bus", bus)

    workflows.publish_workflow_resource(workflow)

    assert events[0].status == "archived"
    assert events[0].project_id is None
