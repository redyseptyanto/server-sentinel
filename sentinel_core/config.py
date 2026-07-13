"""Configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import tomllib


class ConfigurationError(ValueError):
    """Raised when Sentinel configuration is invalid."""


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    id: str = "sentinel-runtime"


@dataclass(frozen=True, slots=True)
class EventBusConfig:
    kind: str = "in_memory"


@dataclass(frozen=True, slots=True)
class AuditConfig:
    enabled: bool = True
    path: Path = Path("var/sentinel/audit.jsonl")


@dataclass(frozen=True, slots=True)
class SentinelConfig:
    runtime: RuntimeConfig = RuntimeConfig()
    event_bus: EventBusConfig = EventBusConfig()
    audit: AuditConfig = AuditConfig()


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
    return SentinelConfig(runtime=runtime, event_bus=event_bus, audit=audit)


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

    return EventBusConfig(kind=kind)


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
