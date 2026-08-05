from __future__ import annotations

import dataclasses
import datetime as dt
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from app.db.session import SessionLocal
from app.events.base import DomainEvent
from app.events.bus import domain_event_bus
from app.repositories.audit_log_repository import AuditLogRepository

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


def _entity(event: DomainEvent) -> tuple[str | None, UUID | None]:
    resource_type = getattr(event, "resource_type", None)
    resource_id = getattr(event, "resource_id", None)
    if resource_type and isinstance(resource_id, UUID):
        return str(resource_type), resource_id

    candidates = (
        ("prompt", "prompt_id"),
        ("workflow", "workflow_id"),
        ("execution", "execution_id"),
        ("usage", "usage_id"),
        ("budget", "budget_id"),
        ("agent", "agent_id"),
    )
    for entity_type, attribute in candidates:
        entity_id = getattr(event, attribute, None)
        if isinstance(entity_id, UUID):
            return entity_type, entity_id
    return None, None


def _action(event: DomainEvent, repository: AuditLogRepository, entity_type: str | None, entity_id: UUID | None) -> str:
    name = event.event_name.lower()
    if name.endswith(("removed", "deleted", "archived")):
        return "delete"
    if name.endswith(("created", "registered")):
        return "create"
    if name.endswith(("published",)):
        return "publish"
    if name in {"workflowexecutionfinished", "aiusagerecorded"} or name.endswith(("executed", "finished")):
        return "execute"
    if name == "resourceupserted":
        if getattr(event, "status", None) == "archived":
            return "delete"
        return "update" if repository.has_entity_event(entity_type=entity_type, entity_id=entity_id) else "create"
    if name.endswith(("updated", "changed", "crossed")):
        return "update"
    return "event"


def _record_audit_log(event: DomainEvent) -> None:
    with SessionLocal() as db:
        repository = AuditLogRepository(db)
        entity_type, entity_id = _entity(event)
        repository.create_once(
            values={
                "event_id": event.event_id,
                "event_name": event.event_name,
                "action": _action(event, repository, entity_type, entity_id),
                "actor_id": event.actor_id or getattr(event, "owner_id", None),
                "project_id": event.project_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "correlation_id": event.correlation_id,
                "payload": _json_safe(event),
                "occurred_at": event.occurred_at,
            }
        )


def register_audit_subscribers() -> None:
    global _registered
    if _registered:
        return
    domain_event_bus.subscribe(DomainEvent, _record_audit_log)
    _registered = True
