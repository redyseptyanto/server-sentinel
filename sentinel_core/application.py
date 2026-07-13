"""Runtime composition root."""

from __future__ import annotations

from dataclasses import dataclass

from sentinel_core.audit import JsonlAuditLog
from sentinel_core.config import SentinelConfig, load_config
from sentinel_core.events import InMemoryEventBus
from sentinel_core.hermes_client import (
    HermesApprovalProvider,
    HermesNotificationHandler,
)
from sentinel_core.runtime import Runtime


@dataclass(frozen=True, slots=True)
class SentinelApplication:
    """Composed Sentinel reference runtime."""

    config: SentinelConfig
    event_bus: InMemoryEventBus
    runtime: Runtime
    audit_log: JsonlAuditLog | None
    hermes_notifier: HermesNotificationHandler | None = None
    hermes_approval_provider: HermesApprovalProvider | None = None

    def start(self) -> None:
        self.runtime.start()

    def stop(self) -> None:
        self.runtime.stop()


def create_application(config: SentinelConfig | None = None) -> SentinelApplication:
    """Create a Sentinel application from validated configuration."""

    resolved_config = config or load_config()
    event_bus = InMemoryEventBus(
        capacity=resolved_config.event_bus.capacity,
        backpressure_strategy=resolved_config.event_bus.backpressure_strategy,
    )

    audit_log = None
    if resolved_config.audit.enabled:
        audit_log = JsonlAuditLog(resolved_config.audit.path)
        event_bus.subscribe(audit_log.record)

    hermes_notifier: HermesNotificationHandler | None = None
    hermes_approval_provider: HermesApprovalProvider | None = None
    if resolved_config.hermes.enabled:
        hermes_notifier = HermesNotificationHandler(config=resolved_config.hermes)
        event_bus.subscribe(
            hermes_notifier.notify,
            event_filter=HermesNotificationHandler.event_filter(
                resolved_config.hermes.notify_on
            ),
        )
        hermes_approval_provider = HermesApprovalProvider(
            config=resolved_config.hermes
        )

    runtime = Runtime(event_bus, runtime_id=resolved_config.runtime.id)
    return SentinelApplication(
        config=resolved_config,
        event_bus=event_bus,
        runtime=runtime,
        audit_log=audit_log,
        hermes_notifier=hermes_notifier,
        hermes_approval_provider=hermes_approval_provider,
    )
