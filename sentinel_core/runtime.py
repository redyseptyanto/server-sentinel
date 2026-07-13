"""Runtime lifecycle implementation."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from sentinel_core.events import Event, EventBus, EventSeverity


class RuntimeState(StrEnum):
    """Runtime lifecycle states."""

    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


class Runtime:
    """Sentinel runtime composition root."""

    def __init__(self, event_bus: EventBus, *, runtime_id: str = "sentinel-runtime") -> None:
        self._event_bus = event_bus
        self._runtime_id = runtime_id
        self._state = RuntimeState.CREATED

    @property
    def state(self) -> RuntimeState:
        return self._state

    def start(self) -> None:
        if self._state == RuntimeState.RUNNING:
            return
        if self._state not in {RuntimeState.CREATED, RuntimeState.STOPPED}:
            raise RuntimeError(f"cannot start runtime from {self._state.value}")

        self._transition_to(RuntimeState.STARTING, reason="start requested")
        self._transition_to(RuntimeState.RUNNING, reason="startup complete")

    def stop(self) -> None:
        if self._state == RuntimeState.STOPPED:
            return
        if self._state == RuntimeState.CREATED:
            self._transition_to(RuntimeState.STOPPED, reason="stop requested before start")
            return
        if self._state != RuntimeState.RUNNING:
            raise RuntimeError(f"cannot stop runtime from {self._state.value}")

        self._transition_to(RuntimeState.STOPPING, reason="stop requested")
        self._transition_to(RuntimeState.STOPPED, reason="shutdown complete")

    def fail(self, reason: str, *, details: dict[str, Any] | None = None) -> None:
        if self._state == RuntimeState.STOPPED:
            raise RuntimeError("cannot fail a stopped runtime")

        self._transition_to(
            RuntimeState.FAILED,
            reason=reason,
            severity=EventSeverity.CRITICAL,
            details=details,
        )

    def _transition_to(
        self,
        next_state: RuntimeState,
        *,
        reason: str,
        severity: EventSeverity = EventSeverity.INFO,
        details: dict[str, Any] | None = None,
    ) -> Event:
        previous_state = self._state
        self._state = next_state
        return self._event_bus.publish(
            Event(
                type="runtime.state_changed",
                source="sentinel.runtime",
                subject=self._runtime_id,
                severity=severity,
                data={
                    "from_state": previous_state.value,
                    "to_state": next_state.value,
                    "reason": reason,
                    "details": details or {},
                },
            )
        )
