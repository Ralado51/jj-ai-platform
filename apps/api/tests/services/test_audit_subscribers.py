import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid4

from app.events import audit_subscribers
from app.events.base import DomainEvent


@dataclass(frozen=True, kw_only=True)
class ExampleCreated(DomainEvent):
    entity_id: UUID
    amount: Decimal


class _SessionContext:
    def __enter__(self):
        return object()

    def __exit__(self, exc_type, exc, traceback):
        return False


class _Repository:
    created_values = None
    existing = False

    def __init__(self, db):
        self.db = db

    def has_entity_event(self, *, entity_type, entity_id):
        return self.existing

    def create_once(self, *, values):
        type(self).created_values = values


def test_audit_subscriber_serializes_domain_event(monkeypatch):
    _Repository.created_values = None
    monkeypatch.setattr(audit_subscribers, "SessionLocal", _SessionContext)
    monkeypatch.setattr(audit_subscribers, "AuditLogRepository", _Repository)
    event = ExampleCreated(
        entity_id=uuid4(),
        actor_id=uuid4(),
        project_id=uuid4(),
        amount=Decimal("1.25"),
        occurred_at=dt.datetime.now(dt.UTC),
    )

    audit_subscribers._record_audit_log(event)

    values = _Repository.created_values
    assert values["event_id"] == event.event_id
    assert values["event_name"] == "ExampleCreated"
    assert values["action"] == "create"
    assert values["payload"]["amount"] == "1.25"
    assert values["payload"]["event_id"] == str(event.event_id)


def test_resource_upsert_is_create_then_update():
    @dataclass(frozen=True, kw_only=True)
    class ResourceUpserted(DomainEvent):
        resource_type: str
        resource_id: UUID
        status: str = "active"

    repository = _Repository(object())
    event = ResourceUpserted(resource_type="workflow", resource_id=uuid4())

    repository.existing = False
    assert audit_subscribers._action(event, repository, "workflow", event.resource_id) == "create"
    repository.existing = True
    assert audit_subscribers._action(event, repository, "workflow", event.resource_id) == "update"
