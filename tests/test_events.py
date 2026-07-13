import unittest

from sentinel_core import (
    EVENT_SCHEMA_VERSION,
    BackpressureStrategy,
    Event,
    EventBusBackpressureError,
    EventSeverity,
    InMemoryEventBus,
)


class EventTests(unittest.TestCase):
    def test_event_requires_identity_fields(self) -> None:
        with self.assertRaises(ValueError):
            Event(type="", source="test", subject="runtime")

        with self.assertRaises(ValueError):
            Event(type="runtime.state_changed", source="", subject="runtime")

        with self.assertRaises(ValueError):
            Event(type="runtime.state_changed", source="test", subject="")

        with self.assertRaises(ValueError):
            Event(
                type="runtime.state_changed",
                source="test",
                subject="runtime",
                schema_version="",
            )

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
        self.assertEqual(event.to_record()["schema_version"], EVENT_SCHEMA_VERSION)
        self.assertEqual(event.to_record()["correlation_id"], "correlation-1")
        self.assertEqual(event.to_record()["causation_id"], "event-0")

    def test_event_uses_default_schema_version(self) -> None:
        event = Event(type="test.event", source="test", subject="runtime")

        self.assertEqual(event.schema_version, EVENT_SCHEMA_VERSION)


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


class InMemoryEventBusBackpressureTests(unittest.TestCase):
    def _make_event(self, n: int) -> Event:
        return Event(type="test.event", source="test", subject=f"runtime-{n}")

    def test_unbounded_bus_retains_all_events(self) -> None:
        bus = InMemoryEventBus()
        for i in range(5):
            bus.publish(self._make_event(i))

        self.assertEqual(len(bus.events), 5)
        self.assertEqual(bus.dropped_count, 0)

    def test_invalid_capacity_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            InMemoryEventBus(capacity=0)

    def test_drop_oldest_keeps_newest_events(self) -> None:
        bus = InMemoryEventBus(capacity=2, backpressure_strategy=BackpressureStrategy.DROP_OLDEST)
        first = self._make_event(0)
        second = self._make_event(1)
        third = self._make_event(2)

        bus.publish(first)
        bus.publish(second)
        bus.publish(third)

        self.assertEqual(bus.events, (second, third))
        self.assertEqual(bus.dropped_count, 1)

    def test_drop_newest_discards_from_buffer_but_still_delivers(self) -> None:
        bus = InMemoryEventBus(capacity=2, backpressure_strategy=BackpressureStrategy.DROP_NEWEST)
        observed: list[Event] = []
        bus.subscribe(observed.append)
        first = self._make_event(0)
        second = self._make_event(1)
        third = self._make_event(2)

        bus.publish(first)
        bus.publish(second)
        bus.publish(third)

        self.assertEqual(bus.events, (first, second))
        self.assertEqual(bus.dropped_count, 1)
        self.assertEqual(observed, [first, second, third])

    def test_reject_strategy_raises_backpressure_error(self) -> None:
        bus = InMemoryEventBus(capacity=1, backpressure_strategy=BackpressureStrategy.REJECT)
        published = bus.publish(self._make_event(0))

        with self.assertRaises(EventBusBackpressureError) as ctx:
            bus.publish(self._make_event(1))

        self.assertEqual(ctx.exception.capacity, 1)
        self.assertEqual(ctx.exception.strategy, BackpressureStrategy.REJECT)
        self.assertEqual(bus.events, (published,))

    def test_backpressure_settings_exposed(self) -> None:
        bus = InMemoryEventBus(capacity=3, backpressure_strategy=BackpressureStrategy.DROP_NEWEST)

        self.assertEqual(bus.capacity, 3)
        self.assertEqual(bus.backpressure_strategy, BackpressureStrategy.DROP_NEWEST)


if __name__ == "__main__":
    unittest.main()
