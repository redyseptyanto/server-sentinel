"""Module entrypoint for `python -m sentinel_core`."""

from __future__ import annotations

from sentinel_core.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
