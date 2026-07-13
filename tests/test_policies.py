import unittest

from sentinel_core import InMemoryEventBus, ThermalPolicy
from sentinel_core.events import Event


class ThermalPolicyTests(unittest.TestCase):
    def test_high_temperature_emits_action_request(self) -> None:
        bus = InMemoryEventBus()
        requests = []
        policy = ThermalPolicy(event_bus=bus, threshold=40.0, action_handler=requests.append)
        policy.subscribe()

        source_event = Event(
            type="sensor.metric_observed",
            source="sensor.cpu",
            subject="host.cpu",
            data={"temperature_celsius": 85.0},
        )
        bus.publish(source_event)

        emitted = [event for event in bus.events if event.type == "policy.action_requested"]
        self.assertEqual(len(emitted), 1)
        self.assertEqual(emitted[0].data["action_type"], "cool_down")
        self.assertEqual(emitted[0].causation_id, source_event.id)
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].action_type, "cool_down")
        self.assertEqual(requests[0].parameters["temperature_celsius"], 85.0)

    def test_temperature_below_threshold_is_ignored(self) -> None:
        bus = InMemoryEventBus()
        requests = []
        policy = ThermalPolicy(event_bus=bus, threshold=40.0, action_handler=requests.append)
        policy.subscribe()

        bus.publish(
            Event(
                type="sensor.metric_observed",
                source="sensor.cpu",
                subject="host.cpu",
                data={"temperature_celsius": 35.0},
            )
        )

        self.assertEqual(
            [event.type for event in bus.events],
            ["sensor.metric_observed"],
        )
        self.assertEqual(requests, [])


if __name__ == "__main__":
    unittest.main()
