"""Configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomllib

from sentinel_core.events import BackpressureStrategy


class ConfigurationError(ValueError):
    """Raised when Sentinel configuration is invalid."""


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    id: str = "sentinel-runtime"


@dataclass(frozen=True, slots=True)
class EventBusConfig:
    kind: str = "in_memory"
    capacity: int | None = None
    backpressure_strategy: BackpressureStrategy = BackpressureStrategy.DROP_OLDEST


@dataclass(frozen=True, slots=True)
class AuditConfig:
    enabled: bool = True
    path: Path = Path("var/sentinel/audit.jsonl")


@dataclass(frozen=True, slots=True)
class HermesConfig:
    enabled: bool = False
    base_url: str = ""
    token: str = ""
    timeout_seconds: float = 10.0
    notify_on: tuple[str, ...] = ("warning", "error", "critical")
    require_approval: bool = True


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    enabled: bool = False
    interval_seconds: int = 5
    temp_threshold_celsius: float = 40.0
    starting_temp_celsius: float = 85.0


@dataclass(frozen=True, slots=True)
class MonitoringConfig:
    enabled: bool = False
    interval_seconds: int = 30
    include_optional: bool = True
    disk_paths: tuple[str, ...] = ("/",)
    temp_threshold_celsius: float = 40.0


@dataclass(frozen=True, slots=True)
class SentinelConfig:
    runtime: RuntimeConfig = RuntimeConfig()
    event_bus: EventBusConfig = EventBusConfig()
    audit: AuditConfig = AuditConfig()
    hermes: HermesConfig = HermesConfig()
    simulation: SimulationConfig = SimulationConfig()
    monitoring: MonitoringConfig = MonitoringConfig()


def load_config(path: str | Path | None = None) -> SentinelConfig:
    """Load configuration from TOML or return defaults when path is omitted."""

    if path is None:
        return config_from_mapping({})

    config_path = Path(path)
    with config_path.open("rb") as config_file:
        return config_from_mapping(tomllib.load(config_file))


def config_from_mapping(raw_config: dict[str, Any]) -> SentinelConfig:
    runtime = _runtime_config(raw_config.get("runtime", {}))
    event_bus = _event_bus_config(raw_config.get("event_bus", {}))
    audit = _audit_config(raw_config.get("audit", {}))
    hermes = _hermes_config(raw_config.get("hermes", {}))
    simulation = _simulation_config(raw_config.get("simulation", {}))
    monitoring = _monitoring_config(raw_config.get("monitoring", {}))
    return SentinelConfig(
        runtime=runtime,
        event_bus=event_bus,
        audit=audit,
        hermes=hermes,
        simulation=simulation,
        monitoring=monitoring,
    )


def _runtime_config(raw_runtime: Any) -> RuntimeConfig:
    if not isinstance(raw_runtime, dict):
        raise ConfigurationError("runtime must be a table")

    runtime_id = raw_runtime.get("id", "sentinel-runtime")
    if not isinstance(runtime_id, str) or not runtime_id.strip():
        raise ConfigurationError("runtime.id must be a non-empty string")

    return RuntimeConfig(id=runtime_id)


def _event_bus_config(raw_event_bus: Any) -> EventBusConfig:
    if not isinstance(raw_event_bus, dict):
        raise ConfigurationError("event_bus must be a table")

    kind = raw_event_bus.get("kind", "in_memory")
    if kind != "in_memory":
        raise ConfigurationError("event_bus.kind must be 'in_memory'")

    capacity = raw_event_bus.get("capacity", None)
    if capacity is not None:
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 1:
            raise ConfigurationError("event_bus.capacity must be a positive integer or null")

    raw_strategy = raw_event_bus.get("backpressure_strategy", "drop_oldest")
    if not isinstance(raw_strategy, str):
        raise ConfigurationError("event_bus.backpressure_strategy must be a string")
    try:
        strategy = BackpressureStrategy(raw_strategy)
    except ValueError:
        allowed = ", ".join(s.value for s in BackpressureStrategy)
        raise ConfigurationError(
            f"event_bus.backpressure_strategy must be one of: {allowed}"
        )

    return EventBusConfig(
        kind=kind,
        capacity=capacity,
        backpressure_strategy=strategy,
    )


def _audit_config(raw_audit: Any) -> AuditConfig:
    if not isinstance(raw_audit, dict):
        raise ConfigurationError("audit must be a table")

    enabled = raw_audit.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ConfigurationError("audit.enabled must be a boolean")

    path = raw_audit.get("path", "var/sentinel/audit.jsonl")
    if enabled and (not isinstance(path, str) or not path.strip()):
        raise ConfigurationError("audit.path must be a non-empty string when audit is enabled")
    if not isinstance(path, str):
        raise ConfigurationError("audit.path must be a string")

    return AuditConfig(enabled=enabled, path=Path(path))


def _hermes_config(raw_hermes: Any) -> HermesConfig:
    if not isinstance(raw_hermes, dict):
        raise ConfigurationError("hermes must be a table")

    enabled = raw_hermes.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ConfigurationError("hermes.enabled must be a boolean")

    base_url = raw_hermes.get("base_url", "")
    if not isinstance(base_url, str):
        raise ConfigurationError("hermes.base_url must be a string")
    if enabled and not base_url.strip():
        raise ConfigurationError("hermes.base_url must be a non-empty string when hermes is enabled")

    token = raw_hermes.get("token", "")
    if not isinstance(token, str):
        raise ConfigurationError("hermes.token must be a string")

    timeout_seconds = raw_hermes.get("timeout_seconds", 10.0)
    if not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool):
        raise ConfigurationError("hermes.timeout_seconds must be a number")
    if timeout_seconds <= 0:
        raise ConfigurationError("hermes.timeout_seconds must be positive")

    notify_on = raw_hermes.get("notify_on", ("warning", "error", "critical"))
    if not isinstance(notify_on, (list, tuple)):
        raise ConfigurationError("hermes.notify_on must be a list of severities")
    for severity in notify_on:
        if not isinstance(severity, str):
            raise ConfigurationError("hermes.notify_on entries must be strings")

    require_approval = raw_hermes.get("require_approval", True)
    if not isinstance(require_approval, bool):
        raise ConfigurationError("hermes.require_approval must be a boolean")

    return HermesConfig(
        enabled=enabled,
        base_url=base_url,
        token=token,
        timeout_seconds=float(timeout_seconds),
        notify_on=tuple(notify_on),
        require_approval=require_approval,
    )


def _simulation_config(raw_simulation: Any) -> SimulationConfig:
    if not isinstance(raw_simulation, dict):
        raise ConfigurationError("simulation must be a table")

    enabled = raw_simulation.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ConfigurationError("simulation.enabled must be a boolean")

    interval_seconds = raw_simulation.get("interval_seconds", 5)
    if (
        not isinstance(interval_seconds, int)
        or isinstance(interval_seconds, bool)
        or interval_seconds <= 0
    ):
        raise ConfigurationError("simulation.interval_seconds must be a positive integer")

    temp_threshold_celsius = raw_simulation.get("temp_threshold_celsius", 40.0)
    if not isinstance(temp_threshold_celsius, (int, float)) or isinstance(
        temp_threshold_celsius, bool
    ):
        raise ConfigurationError("simulation.temp_threshold_celsius must be numeric")

    starting_temp_celsius = raw_simulation.get("starting_temp_celsius", 85.0)
    if not isinstance(starting_temp_celsius, (int, float)) or isinstance(
        starting_temp_celsius, bool
    ):
        raise ConfigurationError("simulation.starting_temp_celsius must be numeric")

    return SimulationConfig(
        enabled=enabled,
        interval_seconds=interval_seconds,
        temp_threshold_celsius=float(temp_threshold_celsius),
        starting_temp_celsius=float(starting_temp_celsius),
    )


def _monitoring_config(raw_monitoring: Any) -> MonitoringConfig:
    if not isinstance(raw_monitoring, dict):
        raise ConfigurationError("monitoring must be a table")

    enabled = raw_monitoring.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ConfigurationError("monitoring.enabled must be a boolean")

    interval_seconds = raw_monitoring.get("interval_seconds", 30)
    if (
        not isinstance(interval_seconds, int)
        or isinstance(interval_seconds, bool)
        or interval_seconds <= 0
    ):
        raise ConfigurationError("monitoring.interval_seconds must be a positive integer")

    include_optional = raw_monitoring.get("include_optional", True)
    if not isinstance(include_optional, bool):
        raise ConfigurationError("monitoring.include_optional must be a boolean")

    disk_paths = raw_monitoring.get("disk_paths", ["/"])
    if not isinstance(disk_paths, (list, tuple)):
        raise ConfigurationError("monitoring.disk_paths must be a list of strings")
    normalized_paths: list[str] = []
    for path in disk_paths:
        if not isinstance(path, str) or not path.strip():
            raise ConfigurationError("monitoring.disk_paths entries must be non-empty strings")
        normalized_paths.append(path)

    temp_threshold_celsius = raw_monitoring.get("temp_threshold_celsius", 40.0)
    if not isinstance(temp_threshold_celsius, (int, float)) or isinstance(
        temp_threshold_celsius, bool
    ):
        raise ConfigurationError("monitoring.temp_threshold_celsius must be numeric")

    return MonitoringConfig(
        enabled=enabled,
        interval_seconds=interval_seconds,
        include_optional=include_optional,
        disk_paths=tuple(normalized_paths),
        temp_threshold_celsius=float(temp_threshold_celsius),
    )
