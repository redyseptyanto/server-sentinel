"""Policy implementations for the Sentinel reference runtime."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sentinel_core.action_audit import ActionRequest, ActionSafety
from sentinel_core.events import Event, EventBus


ActionRequestHandler = Callable[[ActionRequest], None]


@dataclass(slots=True)
class ThermalPolicy:
    """Emit a cooling action request when temperature exceeds a threshold."""

    event_bus: EventBus
    threshold: float = 40.0
    action_handler: ActionRequestHandler | None = None
    source: str = "sentinel.policy.thermal"

    def subscribe(self) -> Callable[[], None]:
        """Subscribe the policy to metric events."""
        return self.event_bus.subscribe(
            self.handle_event,
            event_filter=lambda event: event.type == "sensor.metric_observed",
        )

    def handle_event(self, event: Event) -> Event | None:
        """Process a metric event and emit a `cool_down` action request if needed."""
        temperature = event.data.get("temperature_celsius")
        if not isinstance(temperature, (int, float)) or isinstance(temperature, bool):
            return None
        if float(temperature) <= self.threshold:
            return None

        request = ActionRequest(
            action_type="cool_down",
            subject=event.subject,
            requested_by="policy:thermal",
            safety=ActionSafety.NON_DESTRUCTIVE,
            reason=(
                f"temperature {float(temperature):.1f}C exceeded threshold "
                f"{self.threshold:.1f}C"
            ),
            parameters={
                "temperature_celsius": float(temperature),
                "threshold_celsius": self.threshold,
                "sensor_source": event.source,
            },
            correlation_id=event.correlation_id,
        )
        emitted = self.event_bus.publish(
            Event(
                type="policy.action_requested",
                source=self.source,
                subject=event.subject,
                correlation_id=event.correlation_id,
                causation_id=event.id,
                data={
                    "action_id": request.id,
                    "action_type": request.action_type,
                    "safety": request.safety.value,
                    "requested_by": request.requested_by,
                    "reason": request.reason,
                    "parameters": dict(request.parameters),
                },
            )
        )
        if self.action_handler is not None:
            self.action_handler(request)
        return emitted
