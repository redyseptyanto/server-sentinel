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
        if self.occurred_at.tzinfo is None:
            raise ValueError("event occurred_at must be timezone-aware")
        object.__setattr__(self, "data", MappingProxyType(dict(self.data)))

    def to_record(self) -> dict[str, JsonValue]:
        """Return a JSON-compatible audit/event record."""

        return {
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
    """Synchronous in-memory event bus for the reference runtime."""

    def __init__(self) -> None:
        self._handlers: list[tuple[EventHandler, EventFilter | None]] = []
        self._events: list[Event] = []
        self._lock = RLock()

    def publish(self, event: Event) -> Event:
        with self._lock:
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
