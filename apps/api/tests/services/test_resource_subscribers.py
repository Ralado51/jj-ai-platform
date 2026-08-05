from uuid import uuid4

from app.events import resource_subscribers
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

    def find_registered(self, **kwargs):
        return None

    def create(self, *, owner_id, values):
        type(self).created_values = values


def test_resource_subscriber_maps_metadata_to_orm_attribute(monkeypatch):
    _Repository.created_values = None
    monkeypatch.setattr(resource_subscribers, "SessionLocal", _SessionContext)
    monkeypatch.setattr(resource_subscribers, "ResourceRegistryRepository", _Repository)

    resource_subscribers._upsert_resource(
        ResourceUpserted(
            owner_id=uuid4(),
            resource_type="workflow",
            resource_id=uuid4(),
            name="Content pipeline",
            metadata={"steps_count": 2},
        )
    )

    assert _Repository.created_values["resource_metadata"] == {"steps_count": 2}
    assert "metadata" not in _Repository.created_values
