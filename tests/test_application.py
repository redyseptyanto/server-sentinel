import json
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


if __name__ == "__main__":
    unittest.main()
