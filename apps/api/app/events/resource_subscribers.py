from __future__ import annotations

from app.db.session import SessionLocal
from app.events.bus import domain_event_bus
from app.events.resource_events import ResourceRemoved, ResourceUpserted
from app.events.types import PromptArchived, PromptCreated, PromptUpdated
from app.repositories.resource_registry_repository import ResourceRegistryRepository

_registered = False


def _upsert_resource(event: ResourceUpserted) -> None:
    with SessionLocal() as db:
        repository = ResourceRegistryRepository(db)
        item = repository.find_registered(
            owner_id=event.owner_id,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
        )
        values = {
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "project_id": event.project_id,
            "name": event.name,
            "description": event.description,
            "status": event.status,
            "labels": event.labels,
            "resource_metadata": event.metadata,
        }
        if item is None:
            repository.create(owner_id=event.owner_id, values=values)
        else:
            repository.update(item=item, values=values)


def _remove_resource(event: ResourceRemoved) -> None:
    with SessionLocal() as db:
        repository = ResourceRegistryRepository(db)
        item = repository.find_registered(
            owner_id=event.owner_id,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
        )
        if item is not None:
            repository.delete(item=item)


def _upsert_prompt_resource(event: PromptCreated | PromptUpdated | PromptArchived) -> None:
    snapshot = event.current_values
    with SessionLocal() as db:
        repository = ResourceRegistryRepository(db)
        item = repository.find_registered(
            owner_id=event.owner_id,
            resource_type="prompt",
            resource_id=event.prompt_id,
        )
        values = {
            "resource_type": "prompt",
            "resource_id": event.prompt_id,
            "project_id": event.project_id,
            "name": snapshot["name"],
            "description": snapshot.get("description"),
            "status": "active" if snapshot.get("is_active", True) else "archived",
            "labels": [snapshot.get("category", "general")],
            "resource_metadata": {
                "variables": snapshot.get("variables", []),
                "is_public": snapshot.get("is_public", False),
            },
        }
        if item is None:
            repository.create(owner_id=event.owner_id, values=values)
        else:
            repository.update(item=item, values=values)


def register_resource_subscribers() -> None:
    global _registered
    if _registered:
        return
    domain_event_bus.subscribe(ResourceUpserted, _upsert_resource)
    domain_event_bus.subscribe(ResourceRemoved, _remove_resource)
    domain_event_bus.subscribe(PromptCreated, _upsert_prompt_resource)
    domain_event_bus.subscribe(PromptUpdated, _upsert_prompt_resource)
    domain_event_bus.subscribe(PromptArchived, _upsert_prompt_resource)
    _registered = True
