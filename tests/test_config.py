import tempfile
import unittest
from pathlib import Path

from sentinel_core import (
    BackpressureStrategy,
    ConfigurationError,
    HermesConfig,
    config_from_mapping,
    load_config,
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


if __name__ == "__main__":
    unittest.main()
