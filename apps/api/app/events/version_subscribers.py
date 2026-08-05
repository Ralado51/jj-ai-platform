from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from app.db.session import SessionLocal
from app.events.bus import domain_event_bus
from app.events.resource_events import ResourceUpserted
from app.repositories.resource_version_repository import ResourceVersionRepository

_registered = False


def _json_safe(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if dataclasses.is_dataclass(value):
        return _json_safe(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return value


def _snapshot(event: ResourceUpserted) -> dict:
    return _json_safe(
        {
            "name": event.name,
            "description": event.description,
            "status": event.status,
            "labels": sorted(event.labels),
            "metadata": event.metadata,
        }
    )


def _checksum(snapshot: dict) -> str:
    encoded = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
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
