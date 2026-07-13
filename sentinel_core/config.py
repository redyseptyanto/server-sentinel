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
class ThermalPolicyConfig:
    warning_cpu_threshold_celsius: float = 70.0
    warning_nvme_threshold_celsius: float = 80.0
    rearm_below_celsius: float = 60.0
    critical_cpu_threshold_celsius: float = 85.0
    emergency_cpu_threshold_celsius: float = 95.0
    emergency_hold_seconds: float = 30.0
    approval_timeout_seconds: float = 30.0
    protected_process_patterns: tuple[str, ...] = (
        "systemd",
        "sshd",
        "NetworkManager",
        "dbus-daemon",
        "dockerd",
        "containerd",
        "postgres",
        "mysqld",
        "mongod",
    )
    top_process_count: int = 3


@dataclass(frozen=True, slots=True)
class SentinelConfig:
    runtime: RuntimeConfig = RuntimeConfig()
    event_bus: EventBusConfig = EventBusConfig()
    audit: AuditConfig = AuditConfig()
    hermes: HermesConfig = HermesConfig()
    simulation: SimulationConfig = SimulationConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    thermal_policy: ThermalPolicyConfig = ThermalPolicyConfig()


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
    thermal_policy = _thermal_policy_config(raw_config.get("thermal_policy", {}))
    return SentinelConfig(
        runtime=runtime,
        event_bus=event_bus,
        audit=audit,
        hermes=hermes,
        simulation=simulation,
        monitoring=monitoring,
        thermal_policy=thermal_policy,
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


def _thermal_policy_config(raw_policy: Any) -> ThermalPolicyConfig:
    if not isinstance(raw_policy, dict):
        raise ConfigurationError("thermal_policy must be a table")

    warning_cpu = _require_numeric(
        raw_policy.get("warning_cpu_threshold_celsius", 70.0),
        "thermal_policy.warning_cpu_threshold_celsius",
    )
    warning_nvme = _require_numeric(
        raw_policy.get("warning_nvme_threshold_celsius", 80.0),
        "thermal_policy.warning_nvme_threshold_celsius",
    )
    rearm_below = _require_numeric(
        raw_policy.get("rearm_below_celsius", 60.0),
        "thermal_policy.rearm_below_celsius",
    )
    critical_cpu = _require_numeric(
        raw_policy.get("critical_cpu_threshold_celsius", 85.0),
        "thermal_policy.critical_cpu_threshold_celsius",
    )
    emergency_cpu = _require_numeric(
        raw_policy.get("emergency_cpu_threshold_celsius", 95.0),
        "thermal_policy.emergency_cpu_threshold_celsius",
    )
    emergency_hold_seconds = _require_positive_numeric(
        raw_policy.get("emergency_hold_seconds", 30.0),
        "thermal_policy.emergency_hold_seconds",
    )
    approval_timeout_seconds = _require_positive_numeric(
        raw_policy.get("approval_timeout_seconds", 30.0),
        "thermal_policy.approval_timeout_seconds",
    )

    protected = raw_policy.get(
        "protected_process_patterns",
        [
            "systemd",
            "sshd",
            "NetworkManager",
            "dbus-daemon",
            "dockerd",
            "containerd",
            "postgres",
            "mysqld",
            "mongod",
        ],
    )
    if not isinstance(protected, (list, tuple)):
        raise ConfigurationError(
            "thermal_policy.protected_process_patterns must be a list of strings"
        )
    normalized_patterns: list[str] = []
    for pattern in protected:
        if not isinstance(pattern, str) or not pattern.strip():
            raise ConfigurationError(
                "thermal_policy.protected_process_patterns entries must be non-empty strings"
            )
        normalized_patterns.append(pattern)

    top_process_count = raw_policy.get("top_process_count", 3)
    if (
        not isinstance(top_process_count, int)
        or isinstance(top_process_count, bool)
        or top_process_count <= 0
    ):
        raise ConfigurationError("thermal_policy.top_process_count must be a positive integer")

    if rearm_below >= warning_cpu:
        raise ConfigurationError(
            "thermal_policy.rearm_below_celsius must be lower than warning_cpu_threshold_celsius"
        )
    if rearm_below >= warning_nvme:
        raise ConfigurationError(
            "thermal_policy.rearm_below_celsius must be lower than warning_nvme_threshold_celsius"
        )
    if warning_cpu >= critical_cpu:
        raise ConfigurationError(
            "thermal_policy.warning_cpu_threshold_celsius must be lower than critical_cpu_threshold_celsius"
        )
    if critical_cpu >= emergency_cpu:
        raise ConfigurationError(
            "thermal_policy.critical_cpu_threshold_celsius must be lower than emergency_cpu_threshold_celsius"
        )

    return ThermalPolicyConfig(
        warning_cpu_threshold_celsius=warning_cpu,
        warning_nvme_threshold_celsius=warning_nvme,
        rearm_below_celsius=rearm_below,
        critical_cpu_threshold_celsius=critical_cpu,
        emergency_cpu_threshold_celsius=emergency_cpu,
        emergency_hold_seconds=emergency_hold_seconds,
        approval_timeout_seconds=approval_timeout_seconds,
        protected_process_patterns=tuple(normalized_patterns),
        top_process_count=top_process_count,
    )


def _require_numeric(value: Any, field_name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ConfigurationError(f"{field_name} must be numeric")
    return float(value)


def _require_positive_numeric(value: Any, field_name: str) -> float:
    parsed = _require_numeric(value, field_name)
    if parsed <= 0:
        raise ConfigurationError(f"{field_name} must be positive")
    return parsed
