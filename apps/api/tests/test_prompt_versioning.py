from types import SimpleNamespace
from uuid import uuid4

from app.events import version_subscribers
from app.events.types import PromptArchived, PromptCreated, PromptUpdated
from app.models.user import UserRole
from app.schemas.prompt_template import PromptTemplateCreate, PromptTemplateUpdate
from app.services.prompt_template_service import PromptTemplateService


class FakeEventBus:
    def __init__(self) -> None:
        self.events = []

    def publish(self, event) -> None:
        self.events.append(event)


class FakeRepository:
    def __init__(self) -> None:
        self.items = {}

    def create(self, data, owner_id):
        item = SimpleNamespace(
            id=uuid4(),
            owner_id=owner_id,
            project_id=data.project_id,
            name=data.name,
            description=data.description,
            category=data.category,
            content=data.content,
            variables=data.variables,
            is_public=data.is_public,
            is_favorite=data.is_favorite,
            is_active=data.is_active,
            metadata_=data.metadata,
        )
        self.items[item.id] = item
        return item

    def get_by_id(self, item_id):
        return self.items.get(item_id)

    def update(self, item, data):
        values = data.model_dump(exclude_unset=True)
        if "metadata" in values:
            values["metadata_"] = values.pop("metadata")
        for field, value in values.items():
            setattr(item, field, value)
        return item

    def archive(self, item):
        item.is_active = False
        return item


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


def make_payload():
    return PromptTemplateCreate(
        name="Summarizer",
        description="Summarizes technical documents",
        category="documentation",
        content="Summarize {{document}}.",
        variables=["document"],
        metadata={"model": "gpt-5"},
    )


def test_prompt_lifecycle_publishes_complete_snapshots() -> None:
    repository = FakeRepository()
    event_bus = FakeEventBus()
    service = PromptTemplateService(repository, event_bus)
    user = SimpleNamespace(id=uuid4(), role=UserRole.MEMBER)

    template = service.create(make_payload(), user)
    service.update(
        template.id,
        PromptTemplateUpdate(content="Summarize {{document}} in bullets.", variables=["document"]),
        user,
    )
    service.archive(template.id, user)

    assert isinstance(event_bus.events[0], PromptCreated)
    assert event_bus.events[0].current_values["content"] == "Summarize {{document}}."
    assert isinstance(event_bus.events[1], PromptUpdated)
    assert event_bus.events[1].previous_values["content"] == "Summarize {{document}}."
    assert event_bus.events[1].current_values["content"].endswith("in bullets.")
    assert isinstance(event_bus.events[2], PromptArchived)
    assert event_bus.events[2].current_values["is_active"] is False


def test_restore_creates_a_new_update_event() -> None:
    repository = FakeRepository()
    event_bus = FakeEventBus()
    service = PromptTemplateService(repository, event_bus)
    user = SimpleNamespace(id=uuid4(), role=UserRole.MEMBER)
    template = service.create(make_payload(), user)

    restored = service.restore(
        template.id,
        {
            "name": "Version one",
            "content": "Original {{document}}",
            "variables": ["document"],
            "category": "general",
            "is_active": True,
            "metadata": {"restored": True},
        },
        user,
    )

    assert restored.name == "Version one"
    assert isinstance(event_bus.events[-1], PromptUpdated)
    assert event_bus.events[-1].current_values["metadata"] == {"restored": True}


def test_prompt_event_is_stored_by_generic_version_engine(monkeypatch) -> None:
    _VersionRepository.created_values = None
    monkeypatch.setattr(version_subscribers, "SessionLocal", _SessionContext)
    monkeypatch.setattr(version_subscribers, "ResourceVersionRepository", _VersionRepository)
    event = PromptUpdated(
        actor_id=uuid4(),
        owner_id=uuid4(),
        project_id=uuid4(),
        prompt_id=uuid4(),
        previous_values={"content": "Before"},
        current_values={"content": "After", "variables": []},
    )

    version_subscribers._record_prompt_version(event)

    values = _VersionRepository.created_values
    assert values["event_id"] == event.event_id
    assert values["resource_type"] == "prompt"
    assert values["resource_id"] == event.prompt_id
    assert values["snapshot"] == {"content": "After", "variables": []}
    assert len(values["checksum"]) == 64
