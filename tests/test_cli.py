from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from sentinel_core.cli import main


class CliTests(unittest.TestCase):
    def test_validate_config_prints_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "sentinel.toml"
            config_path.write_text(
                "\n".join(
                    [
                        "[runtime]",
                        'id = "ubuntu-host"',
                        "",
                        "[audit]",
                        "enabled = false",
                        'path = "var/sentinel/audit.jsonl"',
                    ]
                ),
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["validate-config", "--config", str(config_path)])

            self.assertEqual(exit_code, 0)
            rendered = output.getvalue()
            self.assertIn("Config valid:", rendered)
            self.assertIn("runtime.id=ubuntu-host", rendered)

    def test_run_starts_simulation_and_stops_after_duration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "sentinel.toml"
            audit_path = Path(temp_dir) / "audit.jsonl"
            config_path.write_text(
                "\n".join(
                    [
                        "[runtime]",
                        'id = "sim-host"',
                        "",
                        "[audit]",
                        "enabled = true",
                        f'path = "{audit_path.as_posix()}"',
                        "",
                        "[simulation]",
                        "enabled = true",
                        "interval_seconds = 1",
                        "starting_temp_celsius = 85.0",
                    ]
                ),
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "run",
                        "--config",
                        str(config_path),
                        "--duration-seconds",
                        "1.2",
                    ]
                )

            self.assertEqual(exit_code, 0)
            rendered = output.getvalue()
            self.assertIn("Sentinel running with config:", rendered)
            self.assertIn("Sentinel stopped.", rendered)

            records = [
                json.loads(line)
                for line in audit_path.read_text(encoding="utf-8").splitlines()
            ]
            event_types = [record["type"] for record in records]
            self.assertIn("sensor.metric_observed", event_types)
            self.assertIn("policy.action_requested", event_types)
            self.assertIn("action.requested", event_types)
            self.assertIn("action.approval_required", event_types)
            self.assertIn("approval.decision_recorded", event_types)


if __name__ == "__main__":
    unittest.main()
