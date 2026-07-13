"""Deterministic tick-driven scheduler."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sentinel_core.events import Event, EventBus, EventSeverity


class SchedulerError(ValueError):
    """Raised when scheduler state or input is invalid."""


JobHandler = Callable[[], None]


@dataclass(frozen=True, slots=True)
class ScheduledJob:
    """A recurring scheduler job."""

    id: str
    interval_seconds: int
    handler: JobHandler

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise SchedulerError("job id must be a non-empty string")
        if not isinstance(self.interval_seconds, int) or self.interval_seconds <= 0:
            raise SchedulerError("job interval_seconds must be a positive integer")

    @property
    def interval(self) -> timedelta:
        return timedelta(seconds=self.interval_seconds)


@dataclass(slots=True)
class _RegisteredJob:
    job: ScheduledJob
    next_run_at: datetime


class Scheduler:
    """Synchronous scheduler driven by explicit ticks."""

    def __init__(self, event_bus: EventBus, *, source: str = "sentinel.scheduler") -> None:
        self._event_bus = event_bus
        self._source = source
        self._jobs: dict[str, _RegisteredJob] = {}

    def register(self, job: ScheduledJob, *, now: datetime | None = None) -> None:
        if job.id in self._jobs:
            raise SchedulerError(f"job already registered: {job.id}")

        current_time = _resolve_time(now)
        next_run_at = current_time + job.interval
        self._jobs[job.id] = _RegisteredJob(job=job, next_run_at=next_run_at)
        self._publish(
            "scheduler.job_registered",
            job,
            {
                "interval_seconds": job.interval_seconds,
                "next_run_at": next_run_at.isoformat(),
            },
        )

    def unregister(self, job_id: str) -> None:
        if job_id not in self._jobs:
            raise SchedulerError(f"job is not registered: {job_id}")

        registered = self._jobs.pop(job_id)
        self._publish("scheduler.job_unregistered", registered.job, {})

    def due_jobs(self, *, now: datetime | None = None) -> tuple[ScheduledJob, ...]:
        current_time = _resolve_time(now)
        return tuple(
            registered.job
            for registered in self._jobs.values()
            if registered.next_run_at <= current_time
        )

    def run_due(self, *, now: datetime | None = None) -> tuple[ScheduledJob, ...]:
        current_time = _resolve_time(now)
        ran_jobs: list[ScheduledJob] = []
        for registered in tuple(self._jobs.values()):
            if registered.next_run_at > current_time:
                continue

            job = registered.job
            self._publish(
                "scheduler.job_due",
                job,
                {"scheduled_for": registered.next_run_at.isoformat()},
            )
            self._publish("scheduler.job_started", job, {})
            try:
                job.handler()
            except Exception as error:
                registered.next_run_at = current_time + job.interval
                self._publish(
                    "scheduler.job_failed",
                    job,
                    {"error": str(error)},
                    severity=EventSeverity.ERROR,
                )
                raise

            registered.next_run_at = current_time + job.interval
            self._publish(
                "scheduler.job_completed",
                job,
                {"next_run_at": registered.next_run_at.isoformat()},
            )
            ran_jobs.append(job)

        return tuple(ran_jobs)

    def _publish(
        self,
        event_type: str,
        job: ScheduledJob,
        data: dict[str, Any],
        *,
        severity: EventSeverity = EventSeverity.INFO,
    ) -> Event:
        return self._event_bus.publish(
            Event(
                type=event_type,
                source=self._source,
                subject=f"scheduler-job:{job.id}",
                severity=severity,
                data={"job_id": job.id, **data},
            )
        )


def _resolve_time(value: datetime | None) -> datetime:
    resolved = value or datetime.now(UTC)
    if resolved.tzinfo is None:
        raise SchedulerError("scheduler timestamps must be timezone-aware")
    return resolved
