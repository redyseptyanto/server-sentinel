"""Command-line interface for the Sentinel reference runtime."""

from __future__ import annotations

import argparse
import signal
from threading import Event as ThreadEvent
from time import sleep

from sentinel_core.application import create_application
from sentinel_core.config import SentinelConfig, load_config


def build_parser() -> argparse.ArgumentParser:
    """Build the Sentinel CLI parser."""

    parser = argparse.ArgumentParser(prog="sentinel", description="Sentinel runtime CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="start the Sentinel runtime")
    run_parser.add_argument(
        "--config",
        default="sentinel.toml",
        help="path to the Sentinel TOML config file",
    )
    run_parser.add_argument(
        "--duration-seconds",
        type=float,
        default=None,
        help="optional max runtime before exiting cleanly",
    )
    run_parser.set_defaults(handler=_handle_run)

    validate_parser = subparsers.add_parser(
        "validate-config",
        help="validate a Sentinel TOML config file",
    )
    validate_parser.add_argument(
        "--config",
        default="sentinel.toml",
        help="path to the Sentinel TOML config file",
    )
    validate_parser.set_defaults(handler=_handle_validate_config)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the Sentinel CLI and return an exit code."""

    parser = build_parser()
    args = parser.parse_args(argv)
    handler = args.handler
    return int(handler(args))


def _handle_run(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    app = create_application(config)
    stop_event = ThreadEvent()
    _install_signal_handlers(stop_event)

    app.start()
    print(f"Sentinel running with config: {args.config}")
    try:
        _wait_until_stopped(stop_event, duration_seconds=args.duration_seconds)
    finally:
        app.stop()
        print("Sentinel stopped.")
    return 0


def _handle_validate_config(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    _print_valid_config_summary(config, args.config)
    return 0


def _install_signal_handlers(stop_event: ThreadEvent) -> None:
    def _stop_handler(signum: int, frame: object) -> None:
        del frame
        print(f"Received signal {signum}, shutting down...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _stop_handler)
        except ValueError:
            # Signal registration can fail outside the main thread.
            continue


def _wait_until_stopped(
    stop_event: ThreadEvent,
    *,
    duration_seconds: float | None,
) -> None:
    if duration_seconds is not None:
        stop_event.wait(timeout=duration_seconds)
        return

    while not stop_event.is_set():
        sleep(0.25)


def _print_valid_config_summary(config: SentinelConfig, path: str) -> None:
    print(f"Config valid: {path}")
    print(f"runtime.id={config.runtime.id}")
    print(f"audit.enabled={config.audit.enabled}")
    print(f"hermes.enabled={config.hermes.enabled}")
    print(f"simulation.enabled={config.simulation.enabled}")
