import unittest

from sentinel_core import Event, EventSeverity, InMemoryEventBus


class EventTests(unittest.TestCase):
    def test_event_requires_identity_fields(self) -> None:
        with self.assertRaises(ValueError):
            Event(type="", source="test", subject="runtime")

        with self.assertRaises(ValueError):
            Event(type="runtime.state_changed", source="", subject="runtime")

        with self.assertRaises(ValueError):
            Event(type="runtime.state_changed", source="test", subject="")

    def test_event_record_is_json_compatible(self) -> None:
        event = Event(
            type="runtime.state_changed",
            source="sentinel.runtime",
            subject="sentinel-runtime",
            severity=EventSeverity.INFO,
            data={"from_state": "created", "to_state": "starting"},
            correlation_id="correlation-1",
            causation_id="event-0",
        )

        self.assertEqual(event.to_record()["type"], "runtime.state_changed")
        self.assertEqual(event.to_record()["severity"], "info")
        self.assertEqual(event.to_record()["correlation_id"], "correlation-1")
        self.assertEqual(event.to_record()["causation_id"], "event-0")


class InMemoryEventBusTests(unittest.TestCase):
    def test_publish_records_event_and_notifies_subscribers(self) -> None:
        bus = InMemoryEventBus()
        observed: list[Event] = []
        bus.subscribe(observed.append)
        event = Event(type="test.event", source="test", subject="runtime")

        published = bus.publish(event)

        self.assertIs(published, event)
        self.assertEqual(bus.events, (event,))
        self.assertEqual(observed, [event])

    def test_unsubscribe_removes_handler(self) -> None:
        bus = InMemoryEventBus()
        observed: list[Event] = []
        unsubscribe = bus.subscribe(observed.append)
        unsubscribe()

        bus.publish(Event(type="test.event", source="test", subject="runtime"))

        self.assertEqual(observed, [])

    def test_subscribe_can_filter_events(self) -> None:
        bus = InMemoryEventBus()
        observed: list[Event] = []
        bus.subscribe(
            observed.append,
            event_filter=lambda event: event.type == "runtime.state_changed",
        )
        runtime_event = Event(
            type="runtime.state_changed",
            source="sentinel.runtime",
            subject="runtime",
        )
        sensor_event = Event(
            type="sensor.metric_observed",
            source="sensor.cpu",
            subject="host",
        )

        bus.publish(sensor_event)
        bus.publish(runtime_event)

        self.assertEqual(observed, [runtime_event])


if __name__ == "__main__":
    unittest.main()
