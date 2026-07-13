import unittest
from datetime import UTC, datetime, timedelta

from sentinel_core import InMemoryEventBus, ThermalPolicy, ThermalPolicyConfig
from sentinel_core.events import Event


class ThermalPolicyTests(unittest.TestCase):
    def test_warning_temperature_emits_incident_once_per_incident(self) -> None:
        bus = InMemoryEventBus()
        requests = []
        policy = ThermalPolicy(
            event_bus=bus,
            config=ThermalPolicyConfig(
                warning_cpu_threshold_celsius=70.0,
                critical_cpu_threshold_celsius=85.0,
                emergency_cpu_threshold_celsius=95.0,
                rearm_below_celsius=60.0,
            ),
            action_handler=requests.append,
        )
        policy.subscribe()

        bus.publish(
            Event(
                type="sensor.metric_observed",
                source="sensor.cpu",
                subject="host.cpu",
                data={"temperature_celsius": 72.0},
            )
        )
        bus.publish(
            Event(
                type="sensor.metric_observed",
                source="sensor.cpu",
                subject="host.cpu",
                data={"temperature_celsius": 74.0},
            )
        )

        emitted = [event for event in bus.events if event.type == "cpu.temperature.warning"]
        self.assertEqual(len(emitted), 1)
        self.assertEqual(requests, [])
        self.assertEqual(emitted[0].data["temperature_celsius"], 72.0)

    def test_critical_temperature_emits_action_request_with_unprotected_candidates(self) -> None:
        bus = InMemoryEventBus()
        requests = []
        policy = ThermalPolicy(
            event_bus=bus,
            config=ThermalPolicyConfig(
                warning_cpu_threshold_celsius=70.0,
                critical_cpu_threshold_celsius=85.0,
                emergency_cpu_threshold_celsius=95.0,
                protected_process_patterns=("systemd", "sshd"),
                top_process_count=3,
            ),
            action_handler=requests.append,
        )
        policy.subscribe()

        bus.publish(
            Event(
                type="sensor.metric_observed",
                source="sensor.processes",
                subject="host.processes",
                data={
                    "process_count": 64,
                    "top_cpu_processes": [
                        {"pid": 1, "name": "systemd", "cpu_percent": 30.0},
                        {"pid": 222, "name": "python-worker", "cpu_percent": 22.0},
                        {"pid": 333, "name": "ffmpeg", "cpu_percent": 18.0},
                    ],
                    "top_memory_processes": [],
                },
            )
        )
        source_event = Event(
            type="sensor.metric_observed",
            source="sensor.cpu",
            subject="host.cpu",
            data={"temperature_celsius": 87.0, "utilization_percent": 96.5},
        )
        bus.publish(source_event)

        self.assertEqual(
            [event.type for event in bus.events if event.type.startswith("cpu.temperature.")],
            ["cpu.temperature.warning", "cpu.temperature.critical"],
        )
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].action_type, "terminate_processes")
        self.assertEqual(requests[0].parameters["temperature_celsius"], 87.0)
        candidates = requests[0].parameters["termination_candidates"]
        self.assertEqual([candidate["name"] for candidate in candidates], ["python-worker", "ffmpeg"])
        emitted = [event for event in bus.events if event.type == "policy.action_requested"]
        self.assertEqual(emitted[-1].causation_id, source_event.id)

    def test_emergency_temperature_escalates_after_hold_and_timeout(self) -> None:
        bus = InMemoryEventBus()
        requests = []
        policy = ThermalPolicy(
            event_bus=bus,
            config=ThermalPolicyConfig(
                warning_cpu_threshold_celsius=70.0,
                critical_cpu_threshold_celsius=85.0,
                emergency_cpu_threshold_celsius=95.0,
                emergency_hold_seconds=30.0,
                approval_timeout_seconds=10.0,
            ),
            action_handler=requests.append,
        )
        policy.subscribe()

        started_at = datetime(2026, 7, 13, 0, 0, tzinfo=UTC)
        bus.publish(
            Event(
                type="sensor.metric_observed",
                source="sensor.cpu",
                subject="host.cpu",
                occurred_at=started_at,
                data={"temperature_celsius": 96.0},
            )
        )
        bus.publish(
            Event(
                type="sensor.metric_observed",
                source="sensor.cpu",
                subject="host.cpu",
                occurred_at=started_at + timedelta(seconds=31),
                data={"temperature_celsius": 96.0},
            )
        )
        bus.publish(
            Event(
                type="sensor.metric_observed",
                source="sensor.cpu",
                subject="host.cpu",
                occurred_at=started_at + timedelta(seconds=42),
                data={"temperature_celsius": 96.0},
            )
        )

        self.assertEqual(
            [request.action_type for request in requests],
            ["terminate_processes", "reduce_workload", "shutdown_host"],
        )
        incident_types = [event.type for event in bus.events if event.type.startswith("cpu.temperature.")]
        self.assertEqual(
            incident_types,
            ["cpu.temperature.warning", "cpu.temperature.critical", "cpu.temperature.emergency"],
        )

    def test_recovery_rearms_warning_after_temperature_cools(self) -> None:
        bus = InMemoryEventBus()
        policy = ThermalPolicy(
            event_bus=bus,
            config=ThermalPolicyConfig(
                warning_cpu_threshold_celsius=70.0,
                rearm_below_celsius=60.0,
            ),
        )
        policy.subscribe()

        bus.publish(
            Event(
                type="sensor.metric_observed",
                source="sensor.cpu",
                subject="host.cpu",
                data={"temperature_celsius": 75.0},
            )
        )
        bus.publish(
            Event(
                type="sensor.metric_observed",
                source="sensor.cpu",
                subject="host.cpu",
                data={"temperature_celsius": 58.0},
            )
        )
        bus.publish(
            Event(
                type="sensor.metric_observed",
                source="sensor.cpu",
                subject="host.cpu",
                data={"temperature_celsius": 71.0},
            )
        )

        self.assertEqual(
            [event.type for event in bus.events if event.type.startswith("cpu.temperature.")],
            ["cpu.temperature.warning", "cpu.temperature.recovered", "cpu.temperature.warning"],
        )

    def test_nvme_warning_emits_once_until_rearmed(self) -> None:
        bus = InMemoryEventBus()
        policy = ThermalPolicy(
            event_bus=bus,
            config=ThermalPolicyConfig(
                warning_nvme_threshold_celsius=80.0,
                rearm_below_celsius=60.0,
            ),
        )
        policy.subscribe()

        bus.publish(
            Event(
                type="sensor.metric_observed",
                source="sensor.storage",
                subject="host.storage_health",
                data={"max_nvme_temperature_celsius": 82.0},
            )
        )
        bus.publish(
            Event(
                type="sensor.metric_observed",
                source="sensor.storage",
                subject="host.storage_health",
                data={"max_nvme_temperature_celsius": 83.0},
            )
        )
        bus.publish(
            Event(
                type="sensor.metric_observed",
                source="sensor.storage",
                subject="host.storage_health",
                data={"max_nvme_temperature_celsius": 55.0},
            )
        )
        bus.publish(
            Event(
                type="sensor.metric_observed",
                source="sensor.storage",
                subject="host.storage_health",
                data={"max_nvme_temperature_celsius": 81.0},
            )
        )

        emitted = [event.type for event in bus.events if event.type == "nvme.temperature.warning"]
        self.assertEqual(emitted, ["nvme.temperature.warning", "nvme.temperature.warning"])


if __name__ == "__main__":
    unittest.main()
