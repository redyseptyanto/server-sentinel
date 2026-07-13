from datetime import UTC, datetime, timedelta
import unittest

from sentinel_core import InMemoryEventBus, ScheduledJob, Scheduler, SchedulerError


class SchedulerTests(unittest.TestCase):
    def test_register_emits_job_registered_event(self) -> None:
        bus = InMemoryEventBus()
        scheduler = Scheduler(bus)
        now = datetime(2026, 7, 13, 0, 0, tzinfo=UTC)

        scheduler.register(ScheduledJob("cpu", 30, lambda: None), now=now)

        self.assertEqual(bus.events[0].type, "scheduler.job_registered")
        self.assertEqual(bus.events[0].data["job_id"], "cpu")
        self.assertEqual(
            bus.events[0].data["next_run_at"],
            (now + timedelta(seconds=30)).isoformat(),
        )

    def test_due_jobs_returns_jobs_at_or_after_next_run(self) -> None:
        bus = InMemoryEventBus()
        scheduler = Scheduler(bus)
        now = datetime(2026, 7, 13, 0, 0, tzinfo=UTC)
        job = ScheduledJob("cpu", 30, lambda: None)

        scheduler.register(job, now=now)

        self.assertEqual(scheduler.due_jobs(now=now + timedelta(seconds=29)), ())
        self.assertEqual(scheduler.due_jobs(now=now + timedelta(seconds=30)), (job,))

    def test_run_due_executes_job_and_emits_events(self) -> None:
        bus = InMemoryEventBus()
        scheduler = Scheduler(bus)
        now = datetime(2026, 7, 13, 0, 0, tzinfo=UTC)
        calls: list[str] = []
        job = ScheduledJob("cpu", 30, lambda: calls.append("ran"))

        scheduler.register(job, now=now)
        ran_jobs = scheduler.run_due(now=now + timedelta(seconds=30))

        self.assertEqual(ran_jobs, (job,))
        self.assertEqual(calls, ["ran"])
        self.assertEqual(
            [event.type for event in bus.events],
            [
                "scheduler.job_registered",
                "scheduler.job_due",
                "scheduler.job_started",
                "scheduler.job_completed",
            ],
        )

    def test_run_due_emits_failure_event_and_reraises(self) -> None:
        bus = InMemoryEventBus()
        scheduler = Scheduler(bus)
        now = datetime(2026, 7, 13, 0, 0, tzinfo=UTC)

        def fail() -> None:
            raise RuntimeError("sensor failed")

        scheduler.register(ScheduledJob("cpu", 30, fail), now=now)

        with self.assertRaises(RuntimeError):
            scheduler.run_due(now=now + timedelta(seconds=30))

        self.assertEqual(bus.events[-1].type, "scheduler.job_failed")
        self.assertEqual(bus.events[-1].severity.value, "error")
        self.assertEqual(bus.events[-1].data["error"], "sensor failed")

    def test_scheduler_rejects_naive_timestamps(self) -> None:
        bus = InMemoryEventBus()
        scheduler = Scheduler(bus)

        with self.assertRaises(SchedulerError):
            scheduler.register(
                ScheduledJob("cpu", 30, lambda: None),
                now=datetime(2026, 7, 13, 0, 0),
            )


if __name__ == "__main__":
    unittest.main()
