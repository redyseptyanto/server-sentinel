import tempfile
import unittest
from pathlib import Path

from sentinel_core import (
    BackpressureStrategy,
    ConfigurationError,
    HermesConfig,
    MonitoringConfig,
    SimulationConfig,
    config_from_mapping,
    load_config,
    ThermalPolicyConfig,
)


class ConfigTests(unittest.TestCase):
    def test_load_config_returns_defaults_without_path(self) -> None:
        config = load_config()

        self.assertEqual(config.runtime.id, "sentinel-runtime")
        self.assertEqual(config.event_bus.kind, "in_memory")
        self.assertTrue(config.audit.enabled)
        self.assertEqual(config.audit.path, Path("var/sentinel/audit.jsonl"))

    def test_load_config_reads_toml_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "sentinel.toml"
            config_path.write_text(
                "\n".join(
                    [
                        "[runtime]",
                        'id = "edge-node-1"',
                        "",
                        "[event_bus]",
                        'kind = "in_memory"',
                        "",
                        "[audit]",
                        "enabled = true",
                        'path = "audit/events.jsonl"',
                    ]
                ),
                encoding="utf-8",
            )

            config = load_config(config_path)

            self.assertEqual(config.runtime.id, "edge-node-1")
            self.assertEqual(config.audit.path, Path("audit/events.jsonl"))

    def test_invalid_runtime_id_raises_configuration_error(self) -> None:
        with self.assertRaises(ConfigurationError):
            config_from_mapping({"runtime": {"id": ""}})

    def test_invalid_event_bus_kind_raises_configuration_error(self) -> None:
        with self.assertRaises(ConfigurationError):
            config_from_mapping({"event_bus": {"kind": "remote"}})

    def test_invalid_audit_path_raises_configuration_error(self) -> None:
        with self.assertRaises(ConfigurationError):
            config_from_mapping({"audit": {"enabled": True, "path": ""}})

    def test_event_bus_defaults_are_unbounded(self) -> None:
        config = config_from_mapping({})

        self.assertIsNone(config.event_bus.capacity)
        self.assertEqual(
            config.event_bus.backpressure_strategy, BackpressureStrategy.DROP_OLDEST
        )

    def test_event_bus_capacity_and_strategy_are_parsed(self) -> None:
        config = config_from_mapping(
            {
                "event_bus": {
                    "kind": "in_memory",
                    "capacity": 100,
                    "backpressure_strategy": "drop_newest",
                }
            }
        )

        self.assertEqual(config.event_bus.capacity, 100)
        self.assertEqual(
            config.event_bus.backpressure_strategy, BackpressureStrategy.DROP_NEWEST
        )

    def test_invalid_event_bus_capacity_raises_configuration_error(self) -> None:
        with self.assertRaises(ConfigurationError):
            config_from_mapping({"event_bus": {"capacity": 0}})

        with self.assertRaises(ConfigurationError):
            config_from_mapping({"event_bus": {"capacity": "big"}})

    def test_invalid_event_bus_strategy_raises_configuration_error(self) -> None:
        with self.assertRaises(ConfigurationError):
            config_from_mapping({"event_bus": {"backpressure_strategy": "explode"}})

    def test_hermes_defaults_are_disabled(self) -> None:
        config = config_from_mapping({})

        self.assertFalse(config.hermes.enabled)
        self.assertEqual(config.hermes.base_url, "")
        self.assertEqual(config.hermes.token, "")
        self.assertTrue(config.hermes.require_approval)

    def test_hermes_config_is_parsed(self) -> None:
        config = config_from_mapping(
            {
                "hermes": {
                    "enabled": True,
                    "base_url": "http://hermes:8000",
                    "token": "s3kr3t",
                    "timeout_seconds": 5,
                    "notify_on": ["error", "critical"],
                    "require_approval": False,
                }
            }
        )

        self.assertTrue(config.hermes.enabled)
        self.assertEqual(config.hermes.base_url, "http://hermes:8000")
        self.assertEqual(config.hermes.token, "s3kr3t")
        self.assertEqual(config.hermes.timeout_seconds, 5.0)
        self.assertEqual(config.hermes.notify_on, ("error", "critical"))
        self.assertFalse(config.hermes.require_approval)

    def test_hermes_enabled_requires_base_url(self) -> None:
        with self.assertRaises(ConfigurationError):
            config_from_mapping(
                {"hermes": {"enabled": True, "base_url": ""}}
            )

    def test_hermes_invalid_timeout_raises(self) -> None:
        with self.assertRaises(ConfigurationError):
            config_from_mapping(
                {
                    "hermes": {
                        "enabled": True,
                        "base_url": "http://hermes:8000",
                        "timeout_seconds": 0,
                    }
                }
            )

    def test_hermes_invalid_notify_on_raises(self) -> None:
        with self.assertRaises(ConfigurationError):
            config_from_mapping(
                {
                    "hermes": {
                        "enabled": True,
                        "base_url": "http://hermes:8000",
                        "notify_on": "error",
                    }
                }
            )

    def test_simulation_defaults_are_disabled(self) -> None:
        config = config_from_mapping({})

        self.assertFalse(config.simulation.enabled)
        self.assertEqual(config.simulation.interval_seconds, 5)
        self.assertEqual(config.simulation.temp_threshold_celsius, 40.0)
        self.assertEqual(config.simulation.starting_temp_celsius, 85.0)

    def test_simulation_config_is_parsed(self) -> None:
        config = config_from_mapping(
            {
                "simulation": {
                    "enabled": True,
                    "interval_seconds": 2,
                    "temp_threshold_celsius": 50.0,
                    "starting_temp_celsius": 91.5,
                }
            }
        )

        self.assertTrue(config.simulation.enabled)
        self.assertEqual(config.simulation.interval_seconds, 2)
        self.assertEqual(config.simulation.temp_threshold_celsius, 50.0)
        self.assertEqual(config.simulation.starting_temp_celsius, 91.5)

    def test_invalid_simulation_interval_raises(self) -> None:
        with self.assertRaises(ConfigurationError):
            config_from_mapping({"simulation": {"interval_seconds": 0}})

    def test_invalid_simulation_temperature_raises(self) -> None:
        with self.assertRaises(ConfigurationError):
            config_from_mapping({"simulation": {"temp_threshold_celsius": "hot"}})

        with self.assertRaises(ConfigurationError):
            config_from_mapping({"simulation": {"starting_temp_celsius": "hot"}})

    def test_monitoring_defaults_are_disabled(self) -> None:
        config = config_from_mapping({})

        self.assertFalse(config.monitoring.enabled)
        self.assertEqual(config.monitoring.interval_seconds, 30)
        self.assertTrue(config.monitoring.include_optional)
        self.assertEqual(config.monitoring.disk_paths, ("/",))
        self.assertEqual(config.monitoring.temp_threshold_celsius, 40.0)

    def test_monitoring_config_is_parsed(self) -> None:
        config = config_from_mapping(
            {
                "monitoring": {
                    "enabled": True,
                    "interval_seconds": 15,
                    "include_optional": False,
                    "disk_paths": ["/", "/var"],
                    "temp_threshold_celsius": 55.0,
                }
            }
        )

        self.assertTrue(config.monitoring.enabled)
        self.assertEqual(config.monitoring.interval_seconds, 15)
        self.assertFalse(config.monitoring.include_optional)
        self.assertEqual(config.monitoring.disk_paths, ("/", "/var"))
        self.assertEqual(config.monitoring.temp_threshold_celsius, 55.0)

    def test_invalid_monitoring_config_raises(self) -> None:
        with self.assertRaises(ConfigurationError):
            config_from_mapping({"monitoring": {"interval_seconds": 0}})

        with self.assertRaises(ConfigurationError):
            config_from_mapping({"monitoring": {"include_optional": "yes"}})

        with self.assertRaises(ConfigurationError):
            config_from_mapping({"monitoring": {"disk_paths": ["/", ""]}})

        with self.assertRaises(ConfigurationError):
            config_from_mapping({"monitoring": {"temp_threshold_celsius": "hot"}})

    def test_thermal_policy_defaults_are_loaded(self) -> None:
        config = config_from_mapping({})

        self.assertEqual(config.thermal_policy.warning_cpu_threshold_celsius, 70.0)
        self.assertEqual(config.thermal_policy.warning_nvme_threshold_celsius, 80.0)
        self.assertEqual(config.thermal_policy.rearm_below_celsius, 60.0)
        self.assertEqual(config.thermal_policy.top_process_count, 3)

    def test_thermal_policy_config_is_parsed(self) -> None:
        config = config_from_mapping(
            {
                "thermal_policy": {
                    "warning_cpu_threshold_celsius": 68.0,
                    "warning_nvme_threshold_celsius": 79.0,
                    "rearm_below_celsius": 58.0,
                    "critical_cpu_threshold_celsius": 83.0,
                    "emergency_cpu_threshold_celsius": 93.0,
                    "emergency_hold_seconds": 15,
                    "approval_timeout_seconds": 20,
                    "protected_process_patterns": ["systemd", "sshd"],
                    "top_process_count": 4,
                }
            }
        )

        self.assertEqual(config.thermal_policy.warning_cpu_threshold_celsius, 68.0)
        self.assertEqual(config.thermal_policy.warning_nvme_threshold_celsius, 79.0)
        self.assertEqual(config.thermal_policy.rearm_below_celsius, 58.0)
        self.assertEqual(config.thermal_policy.critical_cpu_threshold_celsius, 83.0)
        self.assertEqual(config.thermal_policy.emergency_cpu_threshold_celsius, 93.0)
        self.assertEqual(config.thermal_policy.emergency_hold_seconds, 15.0)
        self.assertEqual(config.thermal_policy.approval_timeout_seconds, 20.0)
        self.assertEqual(config.thermal_policy.protected_process_patterns, ("systemd", "sshd"))
        self.assertEqual(config.thermal_policy.top_process_count, 4)

    def test_invalid_thermal_policy_config_raises(self) -> None:
        with self.assertRaises(ConfigurationError):
            config_from_mapping({"thermal_policy": {"warning_cpu_threshold_celsius": "hot"}})

        with self.assertRaises(ConfigurationError):
            config_from_mapping({"thermal_policy": {"emergency_hold_seconds": 0}})

        with self.assertRaises(ConfigurationError):
            config_from_mapping({"thermal_policy": {"protected_process_patterns": ["sshd", ""]}})

        with self.assertRaises(ConfigurationError):
            config_from_mapping({"thermal_policy": {"top_process_count": 0}})

        with self.assertRaises(ConfigurationError):
            config_from_mapping(
                {
                    "thermal_policy": {
                        "warning_cpu_threshold_celsius": 90.0,
                        "critical_cpu_threshold_celsius": 85.0,
                    }
                }
            )

        with self.assertRaises(ConfigurationError):
            config_from_mapping(
                {
                    "thermal_policy": {
                        "critical_cpu_threshold_celsius": 96.0,
                        "emergency_cpu_threshold_celsius": 95.0,
                    }
                }
            )


if __name__ == "__main__":
    unittest.main()
