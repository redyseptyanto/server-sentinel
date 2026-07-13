import json
import tempfile
import unittest
from pathlib import Path

from sentinel_core import Event, JsonlAuditLog


class JsonlAuditLogTests(unittest.TestCase):
    def test_record_appends_event_json_line(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_path = Path(temp_dir) / "audit" / "sentinel.jsonl"
            audit = JsonlAuditLog(audit_path)
            event = Event(
                type="runtime.state_changed",
                source="sentinel.runtime",
                subject="sentinel-runtime",
                data={"from_state": "created", "to_state": "starting"},
            )

            audit.record(event)

            records = audit_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(records), 1)
            record = json.loads(records[0])
            self.assertEqual(record["id"], event.id)
            self.assertEqual(record["type"], "runtime.state_changed")
            self.assertEqual(record["data"]["to_state"], "starting")


if __name__ == "__main__":
    unittest.main()
