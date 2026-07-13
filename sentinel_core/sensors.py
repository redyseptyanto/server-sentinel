"""Sensor implementations for the Sentinel reference runtime."""

from __future__ import annotations

from dataclasses import dataclass

from sentinel_core.events import Event, EventBus
from sentinel_core.scheduler import ScheduledJob


@dataclass(frozen=True, slots=True)
class SimulatedCpuSensor:
    """Publishes a fixed CPU temperature on a scheduler cadence."""

    event_bus: EventBus
    starting_temp: float = 85.0
    subject: str = "host.cpu"
    source: str = "sentinel.sensor.simulated_cpu"

    def observe(self) -> Event:
        """Emit a placeholder CPU metric event."""
        return self.event_bus.publish(
            Event(
                type="sensor.metric_observed",
                source=self.source,
                subject=self.subject,
                data={"temperature_celsius": float(self.starting_temp)},
            )
        )

    def scheduled_job(self, interval_seconds: int) -> ScheduledJob:
        """Return the recurring scheduler job for this sensor."""
        return ScheduledJob(
            id="simulated_cpu_sensor",
            interval_seconds=interval_seconds,
            handler=self.observe,
        )
