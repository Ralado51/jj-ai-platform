from __future__ import annotations

import inspect
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.events.base import DomainEvent

logger = logging.getLogger(__name__)

EventT = TypeVar("EventT", bound=DomainEvent)
EventHandler = Callable[[DomainEvent], None | Awaitable[None]]


class DomainEventBus:
    """Small in-process event bus for decoupling application services.

    Handlers are isolated by default: one failure is logged and does not stop
    the remaining subscribers. Tests and critical flows may enable strict mode.
    """

    def __init__(self, *, strict: bool = False) -> None:
        self.strict = strict
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type[EventT], handler: Callable[[EventT], None | Awaitable[None]]) -> None:
        handlers = self._handlers[event_type]
        if handler not in handlers:
            handlers.append(handler)  # type: ignore[arg-type]

    def unsubscribe(self, event_type: type[EventT], handler: Callable[[EventT], None | Awaitable[None]]) -> None:
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)  # type: ignore[arg-type]

    def clear(self) -> None:
        self._handlers.clear()

    def handlers_for(self, event: DomainEvent) -> list[EventHandler]:
        handlers: list[EventHandler] = []
        for event_type, registered in self._handlers.items():
            if isinstance(event, event_type):
                handlers.extend(registered)
        return handlers

    def publish(self, event: DomainEvent) -> None:
        for handler in self.handlers_for(event):
            try:
                result = handler(event)
                if inspect.isawaitable(result):
                    raise RuntimeError("Async handler registered on synchronous publish; use publish_async")
            except Exception:
                logger.exception("Domain event handler failed", extra={"event_name": event.event_name})
                if self.strict:
                    raise

    async def publish_async(self, event: DomainEvent) -> None:
        for handler in self.handlers_for(event):
            try:
                result = handler(event)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logger.exception("Domain event handler failed", extra={"event_name": event.event_name})
                if self.strict:
                    raise


domain_event_bus = DomainEventBus()
