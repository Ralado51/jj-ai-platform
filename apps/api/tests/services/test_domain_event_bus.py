import asyncio
from decimal import Decimal
from uuid import uuid4

import pytest

from app.events import AIUsageRecorded, DomainEvent, DomainEventBus


def _event() -> AIUsageRecorded:
    return AIUsageRecorded(
        usage_id=uuid4(),
        actor_id=uuid4(),
        provider="ollama",
        model="gemma3:4b",
        prompt_tokens=10,
        completion_tokens=5,
        estimated_cost=Decimal("0"),
    )


def test_event_bus_delivers_to_specific_and_base_handlers() -> None:
    bus = DomainEventBus(strict=True)
    received = []

    bus.subscribe(DomainEvent, lambda event: received.append(("base", event.event_name)))
    bus.subscribe(AIUsageRecorded, lambda event: received.append(("specific", event.model)))
    bus.publish(_event())

    assert received == [("base", "AIUsageRecorded"), ("specific", "gemma3:4b")]


def test_event_bus_ignores_duplicate_subscription() -> None:
    bus = DomainEventBus(strict=True)
    received = []

    def handler(event: AIUsageRecorded) -> None:
        received.append(event.usage_id)

    bus.subscribe(AIUsageRecorded, handler)
    bus.subscribe(AIUsageRecorded, handler)
    bus.publish(_event())

    assert len(received) == 1


def test_event_bus_isolates_handler_failures_by_default() -> None:
    bus = DomainEventBus()
    received = []

    def failing(_: AIUsageRecorded) -> None:
        raise RuntimeError("boom")

    bus.subscribe(AIUsageRecorded, failing)
    bus.subscribe(AIUsageRecorded, lambda event: received.append(event.usage_id))
    event = _event()
    bus.publish(event)

    assert received == [event.usage_id]


def test_event_bus_raises_handler_failures_in_strict_mode() -> None:
    bus = DomainEventBus(strict=True)

    def failing(_: AIUsageRecorded) -> None:
        raise RuntimeError("boom")

    bus.subscribe(AIUsageRecorded, failing)

    with pytest.raises(RuntimeError, match="boom"):
        bus.publish(_event())


def test_event_bus_supports_async_handlers() -> None:
    bus = DomainEventBus(strict=True)
    received = []

    async def handler(event: AIUsageRecorded) -> None:
        await asyncio.sleep(0)
        received.append(event.model)

    bus.subscribe(AIUsageRecorded, handler)
    asyncio.run(bus.publish_async(_event()))

    assert received == ["gemma3:4b"]
