from uuid import uuid4

from app.events import version_subscribers
from app.events.resource_events import ResourceUpserted


class _SessionContext:
    def __enter__(self):
        return object()

    def __exit__(self, exc_type, exc, traceback):
        return False


class _Repository:
    created_values = None

    def __init__(self, db):
        self.db = db

    def create_once(self, *, values):
        type(self).created_values = values


def test_resource_upsert_creates_immutable_version_snapshot(monkeypatch):
    _Repository.created_values = None
    monkeypatch.setattr(version_subscribers, "SessionLocal", _SessionContext)
    monkeypatch.setattr(version_subscribers, "ResourceVersionRepository", _Repository)
    event = ResourceUpserted(
        owner_id=uuid4(),
        project_id=uuid4(),
        resource_type="workflow",
        resource_id=uuid4(),
        name="Content pipeline",
        description="Creates content",
        status="active",
        labels=["production", "ai"],
        metadata={"steps_count": 2},
    )

    version_subscribers._record_resource_version(event)

    values = _Repository.created_values
    assert values["event_id"] == event.event_id
    assert values["resource_id"] == event.resource_id
    assert values["snapshot"] == {
        "name": "Content pipeline",
        "description": "Creates content",
        "status": "active",
        "labels": ["ai", "production"],
        "metadata": {"steps_count": 2},
    }
    assert len(values["checksum"]) == 64


def test_checksum_is_stable_for_equivalent_snapshots():
    first = {"name": "Flow", "metadata": {"b": 2, "a": 1}}
    second = {"metadata": {"a": 1, "b": 2}, "name": "Flow"}

    assert version_subscribers._checksum(first) == version_subscribers._checksum(second)
