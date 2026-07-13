"""Sentinel reference runtime core."""

from sentinel_core.audit import JsonlAuditLog
from sentinel_core.application import SentinelApplication, create_application
from sentinel_core.action_audit import (
    ActionAuditError,
    ActionAuditRecorder,
    ActionRequest,
    ActionSafety,
    ApprovalDecision,
)
from sentinel_core.actions import ActionPort, SimulatedCoolDownAction
from sentinel_core.config import (
    AuditConfig,
    ConfigurationError,
    EventBusConfig,
    HermesConfig,
    MonitoringConfig,
    RuntimeConfig,
    SimulationConfig,
    SentinelConfig,
    config_from_mapping,
    load_config,
)
from sentinel_core.cli import build_parser, main
from sentinel_core.events import (
    EVENT_SCHEMA_VERSION,
    BackpressureStrategy,
    Event,
    EventBus,
    EventBusBackpressureError,
    EventFilter,
    EventSeverity,
    InMemoryEventBus,
)
from sentinel_core.hermes_client import (
    HermesApprovalProvider,
    HermesConnectionError,
    HermesNotificationHandler,
)
from sentinel_core.policies import ThermalPolicy
from sentinel_core.ports import ApprovalResult, ApprovalProviderPort, NotificationPort
from sentinel_core.plugins import (
    DiscoveredPluginManifest,
    PLUGIN_MANIFEST_FILENAME,
    PluginCategory,
    PluginManifest,
    PluginManifestError,
    discover_plugin_manifests,
    load_plugin_manifest,
    plugin_manifest_from_mapping,
)
from sentinel_core.runtime import Runtime, RuntimeState
from sentinel_core.scheduler import ScheduledJob, Scheduler, SchedulerError
from sentinel_core.sensors import LinuxCommonSensorPack, SimulatedCpuSensor

__all__ = [
    "ActionAuditError",
    "ActionAuditRecorder",
    "ActionPort",
    "ActionRequest",
    "ActionSafety",
    "AuditConfig",
    "ApprovalDecision",
    "BackpressureStrategy",
    "build_parser",
    "ConfigurationError",
    "EVENT_SCHEMA_VERSION",
    "DiscoveredPluginManifest",
    "Event",
    "EventBusConfig",
    "EventBus",
    "EventBusBackpressureError",
    "EventFilter",
    "EventSeverity",
    "HermesApprovalProvider",
    "HermesConfig",
    "HermesConnectionError",
    "HermesNotificationHandler",
    "ApprovalResult",
    "ApprovalProviderPort",
    "NotificationPort",
    "InMemoryEventBus",
    "JsonlAuditLog",
    "PLUGIN_MANIFEST_FILENAME",
    "PluginCategory",
    "PluginManifest",
    "PluginManifestError",
    "Runtime",
    "RuntimeConfig",
    "RuntimeState",
    "ScheduledJob",
    "Scheduler",
    "SchedulerError",
    "SentinelApplication",
    "SentinelConfig",
    "SimulatedCoolDownAction",
    "SimulatedCpuSensor",
    "SimulationConfig",
    "config_from_mapping",
    "create_application",
    "discover_plugin_manifests",
    "load_plugin_manifest",
    "load_config",
    "LinuxCommonSensorPack",
    "main",
    "MonitoringConfig",
    "plugin_manifest_from_mapping",
    "ThermalPolicy",
]
