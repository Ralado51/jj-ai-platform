import datetime as dt
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.v1.routers.resources import serialize
from app.schemas.resources import ResourceCreateRequest


def test_resource_create_request_accepts_metadata_and_labels():
    payload = ResourceCreateRequest(
        resource_type="workflow",
        resource_id=uuid4(),
        name="Content Factory",
        metadata={"environment": "production", "team": "marketing"},
        labels=["production", "ollama"],
    )

    assert payload.resource_type == "workflow"
    assert payload.metadata["environment"] == "production"
    assert payload.labels == ["production", "ollama"]


def test_resource_create_request_rejects_unknown_type():
    with pytest.raises(ValidationError):
        ResourceCreateRequest(resource_type="unknown", resource_id=uuid4(), name="Invalid")


def test_resource_serialization_maps_internal_metadata_name():
    now = dt.datetime.now(dt.UTC)
    item = SimpleNamespace(
        id=uuid4(),
        owner_id=uuid4(),
        project_id=uuid4(),
        resource_type="agent",
        resource_id=uuid4(),
        name="Marketing Agent",
        description="Creates campaign content",
        status="active",
        resource_metadata={"department": "marketing"},
        labels=["marketing", "production"],
        created_at=now,
        updated_at=now,
    )

    response = serialize(item, is_favorite=True)

    assert response.metadata == {"department": "marketing"}
    assert response.labels == ["marketing", "production"]
    assert response.is_favorite is True
