"""Append-only audit sinks."""

from __future__ import annotations

import json
from pathlib import Path

from sentinel_core.events import Event


class JsonlAuditLog:
    """Append events to a JSON Lines audit file."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def record(self, event: Event) -> None:
        with self._path.open("a", encoding="utf-8") as audit_file:
            json.dump(event.to_record(), audit_file, sort_keys=True)
            audit_file.write("\n")
            audit_file.flush()
