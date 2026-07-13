import tempfile
import unittest
from pathlib import Path

from sentinel_core import ConfigurationError, config_from_mapping, load_config


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


if __name__ == "__main__":
    unittest.main()
