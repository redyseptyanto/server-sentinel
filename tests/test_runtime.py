import unittest

from sentinel_core import InMemoryEventBus, Runtime, RuntimeState


class RuntimeTests(unittest.TestCase):
    def test_start_emits_state_change_events(self) -> None:
        bus = InMemoryEventBus()
        runtime = Runtime(bus)

        runtime.start()

        self.assertEqual(runtime.state, RuntimeState.RUNNING)
        self.assertEqual(
            [event.data["to_state"] for event in bus.events],
            ["starting", "running"],
        )
        self.assertTrue(
            all(event.type == "runtime.state_changed" for event in bus.events)
        )

    def test_stop_emits_state_change_events(self) -> None:
        bus = InMemoryEventBus()
        runtime = Runtime(bus)

        runtime.start()
        runtime.stop()

        self.assertEqual(runtime.state, RuntimeState.STOPPED)
        self.assertEqual(
            [event.data["to_state"] for event in bus.events],
            ["starting", "running", "stopping", "stopped"],
        )

    def test_fail_emits_critical_state_change_event(self) -> None:
        bus = InMemoryEventBus()
        runtime = Runtime(bus)

        runtime.fail("startup exception", details={"error": "boom"})

        self.assertEqual(runtime.state, RuntimeState.FAILED)
        self.assertEqual(bus.events[-1].severity.value, "critical")
        self.assertEqual(bus.events[-1].data["to_state"], "failed")
        self.assertEqual(bus.events[-1].data["details"], {"error": "boom"})


if __name__ == "__main__":
    unittest.main()
