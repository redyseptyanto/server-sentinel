import json
import time
import tempfile
import unittest
from pathlib import Path

from sentinel_core import RuntimeState, config_from_mapping, create_application


class ApplicationTests(unittest.TestCase):
    def test_create_application_wires_runtime_id(self) -> None:
        config = config_from_mapping(
            {
                "runtime": {"id": "edge-node-1"},
                "audit": {"enabled": False, "path": "unused.jsonl"},
            }
        )

        app = create_application(config)
        app.start()

        self.assertEqual(app.runtime.state, RuntimeState.RUNNING)
        self.assertEqual(app.event_bus.events[0].subject, "edge-node-1")
        self.assertIsNone(app.audit_log)

    def test_audit_sink_records_startup_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_path = Path(temp_dir) / "audit.jsonl"
            config = config_from_mapping(
                {
                    "runtime": {"id": "edge-node-2"},
                    "audit": {"enabled": True, "path": str(audit_path)},
                }
            )

            app = create_application(config)
            app.start()

            records = [
                json.loads(line)
                for line in audit_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([record["data"]["to_state"] for record in records], ["starting", "running"])
            self.assertEqual(records[0]["subject"], "edge-node-2")

    def test_simulation_runtime_is_wired_when_enabled(self) -> None:
        config = config_from_mapping(
            {
                "audit": {"enabled": False, "path": "unused.jsonl"},
                "simulation": {
                    "enabled": True,
                    "interval_seconds": 1,
                    "temp_threshold_celsius": 40.0,
                    "starting_temp_celsius": 85.0,
                },
            }
        )

        app = create_application(config)

        self.assertIsNotNone(app.simulation_runtime)
        self.assertIsNotNone(app.thermal_recovery_runtime)
        assert app.simulation_runtime is not None
        self.assertEqual(app.simulation_runtime.interval_seconds, 1)

    def test_simulation_runtime_loops_when_started(self) -> None:
        config = config_from_mapping(
            {
                "audit": {"enabled": False, "path": "unused.jsonl"},
                "simulation": {
                    "enabled": True,
                    "interval_seconds": 1,
                    "temp_threshold_celsius": 40.0,
                    "starting_temp_celsius": 85.0,
                },
            }
        )

        app = create_application(config)
        app.start()
        try:
            time.sleep(1.25)
        finally:
            app.stop()

        event_types = [event.type for event in app.event_bus.events]
        self.assertIn("sensor.metric_observed", event_types)
        self.assertIn("policy.action_requested", event_types)
        self.assertIn("action.requested", event_types)
        self.assertIn("approval.decision_recorded", event_types)

    def test_monitoring_runtime_is_wired_when_enabled(self) -> None:
        config = config_from_mapping(
            {
                "audit": {"enabled": False, "path": "unused.jsonl"},
                "monitoring": {
                    "enabled": True,
                    "interval_seconds": 5,
                    "include_optional": False,
                    "disk_paths": ["/"],
                },
                "thermal_policy": {
                    "warning_cpu_threshold_celsius": 72.0,
                    "top_process_count": 4,
                },
            }
        )

        app = create_application(config)

        self.assertIsNotNone(app.monitoring_runtime)
        self.assertIsNotNone(app.thermal_recovery_runtime)
        assert app.monitoring_runtime is not None
        assert app.thermal_recovery_runtime is not None
        self.assertEqual(app.monitoring_runtime.interval_seconds, 5)
        self.assertEqual(
            app.thermal_recovery_runtime.thermal_policy.config.warning_cpu_threshold_celsius,
            72.0,
        )
        self.assertEqual(app.monitoring_runtime.sensor_pack.top_process_count, 4)


if __name__ == "__main__":
    unittest.main()
