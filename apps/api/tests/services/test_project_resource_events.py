from types import SimpleNamespace
from uuid import uuid4

from app.events.bus import DomainEventBus
from app.events.resource_events import ResourceUpserted
from app.services.project_service import ProjectService


class _Repository:
    def __init__(self, project):
        self.project = project

    def get_by_slug(self, slug):
        return None

    def create(self, data):
        return self.project

    def get_by_id(self, project_id):
        return self.project

    def archive(self, project):
        project.is_active = False
        return project


def test_project_create_publishes_resource_event():
    owner_id = uuid4()
    project = SimpleNamespace(
        id=uuid4(),
        name="Marketing",
        slug="marketing",
        description="Campanhas",
        is_active=True,
    )
    events = []
    bus = DomainEventBus(strict=True)
    bus.subscribe(ResourceUpserted, events.append)
    service = ProjectService(_Repository(project), event_bus=bus)

    service.create(SimpleNamespace(slug="marketing"), owner_id=owner_id)

    assert len(events) == 1
    assert events[0].owner_id == owner_id
    assert events[0].resource_type == "project"
    assert events[0].resource_id == project.id
    assert events[0].status == "active"


def test_project_archive_updates_resource_status():
    owner_id = uuid4()
    project = SimpleNamespace(
        id=uuid4(),
        name="Marketing",
        slug="marketing",
        description=None,
        is_active=True,
    )
    events = []
    bus = DomainEventBus(strict=True)
    bus.subscribe(ResourceUpserted, events.append)
    service = ProjectService(_Repository(project), event_bus=bus)

    service.archive(project.id, owner_id=owner_id)

    assert events[0].status == "archived"
