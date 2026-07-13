from datetime import UTC, datetime, timedelta
import unittest

from sentinel_core import InMemoryEventBus, Scheduler, SimulatedCpuSensor


class SimulatedCpuSensorTests(unittest.TestCase):
    def test_observe_publishes_temperature_event(self) -> None:
        bus = InMemoryEventBus()
        sensor = SimulatedCpuSensor(event_bus=bus, starting_temp=85.0)

        sensor.observe()

        self.assertEqual(bus.events[-1].type, "sensor.metric_observed")
        self.assertEqual(bus.events[-1].data["temperature_celsius"], 85.0)

    def test_sensor_can_be_scheduled(self) -> None:
        bus = InMemoryEventBus()
        scheduler = Scheduler(bus)
        sensor = SimulatedCpuSensor(event_bus=bus, starting_temp=72.5)
        now = datetime(2026, 7, 13, 0, 0, tzinfo=UTC)

        scheduler.register(sensor.scheduled_job(5), now=now)
        scheduler.run_due(now=now + timedelta(seconds=5))

        metric_events = [event for event in bus.events if event.type == "sensor.metric_observed"]
        self.assertEqual(len(metric_events), 1)
        self.assertEqual(metric_events[0].data["temperature_celsius"], 72.5)


if __name__ == "__main__":
    unittest.main()
