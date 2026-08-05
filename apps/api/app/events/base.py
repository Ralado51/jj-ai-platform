from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Immutable fact published after a business operation succeeds."""

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: dt.datetime = field(default_factory=lambda: dt.datetime.now(dt.UTC))
    correlation_id: UUID | None = None
    actor_id: UUID | None = None
    project_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def event_name(self) -> str:
        return self.__class__.__name__
