from __future__ import annotations

import hashlib
import json

from app.db.session import SessionLocal
from app.events.bus import domain_event_bus
from app.events.resource_events import ResourceUpserted
from app.repositories.resource_version_repository import ResourceVersionRepository

_registered = False


def _snapshot(event: ResourceUpserted) -> dict:
    return {
        "name": event.name,
        "description": event.description,
        "status": event.status,
        "labels": sorted(event.labels),
        "metadata": event.metadata,
    }


def _checksum(snapshot: dict) -> str:
    encoded = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _record_resource_version(event: ResourceUpserted) -> None:
    snapshot = _snapshot(event)
    with SessionLocal() as db:
        ResourceVersionRepository(db).create_once(
            values={
                "event_id": event.event_id,
                "owner_id": event.owner_id,
                "project_id": event.project_id,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "snapshot": snapshot,
                "checksum": _checksum(snapshot),
                "occurred_at": event.occurred_at,
            }
        )


def register_version_subscribers() -> None:
    global _registered
    if _registered:
        return
    domain_event_bus.subscribe(ResourceUpserted, _record_resource_version)
    _registered = True
