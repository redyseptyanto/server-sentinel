"""Event contracts and in-memory event bus."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from threading import RLock
from types import MappingProxyType
from typing import Any, Protocol
from uuid import uuid4


JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
EventHandler = Callable[["Event"], None]
EventFilter = Callable[["Event"], bool]
EVENT_SCHEMA_VERSION = "1.0"


class BackpressureStrategy(StrEnum):
    """Strategy applied when the retained event buffer reaches capacity."""

    DROP_OLDEST = "drop_oldest"
    DROP_NEWEST = "drop_newest"
    REJECT = "reject"


class EventBusBackpressureError(RuntimeError):
    """Raised when an event cannot be published because the bus is at capacity."""

    def __init__(self, strategy: BackpressureStrategy, capacity: int) -> None:
        self.strategy = strategy
        self.capacity = capacity
        super().__init__(
            f"event bus at capacity {capacity} with strategy {strategy.value}"
        )


class EventSeverity(StrEnum):
    """Supported event severities."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class Event:
    """Immutable event envelope shared by Sentinel subsystems."""

    type: str
    source: str
    subject: str
    data: dict[str, JsonValue] = field(default_factory=dict)
    severity: EventSeverity = EventSeverity.INFO
    schema_version: str = EVENT_SCHEMA_VERSION
    id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    causation_id: str | None = None

    def __post_init__(self) -> None:
        if not self.type.strip():
            raise ValueError("event type is required")
        if not self.source.strip():
            raise ValueError("event source is required")
        if not self.subject.strip():
            raise ValueError("event subject is required")
        if not self.schema_version.strip():
            raise ValueError("event schema_version is required")
        if self.occurred_at.tzinfo is None:
            raise ValueError("event occurred_at must be timezone-aware")
        object.__setattr__(self, "data", MappingProxyType(dict(self.data)))

    def to_record(self) -> dict[str, JsonValue]:
        """Return a JSON-compatible audit/event record."""

        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "type": self.type,
            "source": self.source,
            "subject": self.subject,
            "occurred_at": self.occurred_at.isoformat(),
            "severity": self.severity.value,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "data": dict(self.data),
        }


class EventBus(Protocol):
    """Event bus port."""

    def publish(self, event: Event) -> Event:
        """Publish an event and return the published event."""

    def subscribe(
        self,
        handler: EventHandler,
        event_filter: EventFilter | None = None,
    ) -> Callable[[], None]:
        """Subscribe a handler and return an unsubscribe function."""


class InMemoryEventBus:
    """Synchronous in-memory event bus for the reference runtime.

    The bus retains a bounded history of published events for diagnostics and
    replay. When the retained buffer reaches ``capacity`` the configured
    ``backpressure_strategy`` decides what happens to the incoming event:

    - ``drop_oldest``: evict the oldest retained event and keep the new one.
    - ``drop_newest``: discard the new event from the retained buffer but still
      deliver it to subscribers.
    - ``reject``: refuse to publish and raise ``EventBusBackpressureError``.

    Subscribers are always notified for events that are not rejected, regardless
    of whether the event is retained. Backpressure only governs the retained
    history, never delivery to live subscribers.
    """

    def __init__(
        self,
        capacity: int | None = None,
        backpressure_strategy: BackpressureStrategy = BackpressureStrategy.DROP_OLDEST,
    ) -> None:
        if capacity is not None and capacity < 1:
            raise ValueError("capacity must be a positive integer or None")

        self._handlers: list[tuple[EventHandler, EventFilter | None]] = []
        self._events: list[Event] = []
        self._capacity = capacity
        self._backpressure_strategy = backpressure_strategy
        self._dropped_count = 0
        self._lock = RLock()

    def publish(self, event: Event) -> Event:
        with self._lock:
            if self._capacity is not None and len(self._events) >= self._capacity:
                if self._backpressure_strategy is BackpressureStrategy.REJECT:
                    raise EventBusBackpressureError(
                        self._backpressure_strategy, self._capacity
                    )
                if self._backpressure_strategy is BackpressureStrategy.DROP_OLDEST:
                    self._events.pop(0)
                    self._events.append(event)
                # DROP_NEWEST keeps the buffer unchanged and skips retention.
                self._dropped_count += 1
            else:
                self._events.append(event)

            handlers = tuple(self._handlers)

        for handler, event_filter in handlers:
            if event_filter is None or event_filter(event):
                handler(event)

        return event

    def subscribe(
        self,
        handler: EventHandler,
        event_filter: EventFilter | None = None,
    ) -> Callable[[], None]:
        subscription = (handler, event_filter)
        with self._lock:
            self._handlers.append(subscription)

        def unsubscribe() -> None:
            with self._lock:
                if subscription in self._handlers:
                    self._handlers.remove(subscription)

        return unsubscribe

    @property
    def events(self) -> tuple[Event, ...]:
        with self._lock:
            return tuple(self._events)

    @property
    def capacity(self) -> int | None:
        return self._capacity

    @property
    def backpressure_strategy(self) -> BackpressureStrategy:
        return self._backpressure_strategy

    @property
    def dropped_count(self) -> int:
        """Count of events dropped from the retained buffer by backpressure."""
        with self._lock:
            return self._dropped_count
