"""Runtime composition root."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Event as ThreadEvent, Thread

from sentinel_core.actions import ActionPort, SimulatedCoolDownAction
from sentinel_core.audit import JsonlAuditLog
from sentinel_core.config import SentinelConfig, load_config
from sentinel_core.events import InMemoryEventBus
from sentinel_core.hermes_client import (
    HermesApprovalProvider,
    HermesNotificationHandler,
)
from sentinel_core.policies import ThermalPolicy
from sentinel_core.runtime import Runtime
from sentinel_core.scheduler import Scheduler
from sentinel_core.sensors import SimulatedCpuSensor


@dataclass(slots=True)
class SimulationRuntime:
    """Managed simulation wiring for the reference runtime."""

    scheduler: Scheduler
    sensor: SimulatedCpuSensor
    thermal_policy: ThermalPolicy
    action_handler: ActionPort
    interval_seconds: int
    _unsubscribe_policy: Callable[[], None] | None = None
    _thread: Thread | None = None
    _stop_event: ThreadEvent | None = None

    def __post_init__(self) -> None:
        self._unsubscribe_policy = self.thermal_policy.subscribe()
        self.scheduler.register(self.sensor.scheduled_job(self.interval_seconds))
        self._stop_event = ThreadEvent()

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        assert self._stop_event is not None
        self._stop_event.clear()
        self._thread = Thread(
            target=self._run_loop,
            name="sentinel-simulation",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        if self._stop_event is None:
            return
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _run_loop(self) -> None:
        assert self._stop_event is not None
        poll_interval = min(max(self.interval_seconds / 10.0, 0.1), 1.0)
        while not self._stop_event.is_set():
            self.scheduler.run_due(now=datetime.now(UTC))
            self._stop_event.wait(poll_interval)


@dataclass(frozen=True, slots=True)
class SentinelApplication:
    """Composed Sentinel reference runtime."""

    config: SentinelConfig
    event_bus: InMemoryEventBus
    runtime: Runtime
    audit_log: JsonlAuditLog | None
    scheduler: Scheduler
    hermes_notifier: HermesNotificationHandler | None = None
    hermes_approval_provider: HermesApprovalProvider | None = None
    simulation_runtime: SimulationRuntime | None = None

    def start(self) -> None:
        self.runtime.start()
        if self.simulation_runtime is not None:
            self.simulation_runtime.start()

    def stop(self) -> None:
        if self.simulation_runtime is not None:
            self.simulation_runtime.stop()
        self.runtime.stop()


def create_application(config: SentinelConfig | None = None) -> SentinelApplication:
    """Create a Sentinel application from validated configuration."""

    resolved_config = config or load_config()
    event_bus = InMemoryEventBus(
        capacity=resolved_config.event_bus.capacity,
        backpressure_strategy=resolved_config.event_bus.backpressure_strategy,
    )
    scheduler = Scheduler(event_bus)

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

    simulation_runtime: SimulationRuntime | None = None
    if resolved_config.simulation.enabled:
        sensor = SimulatedCpuSensor(
            event_bus=event_bus,
            starting_temp=resolved_config.simulation.starting_temp_celsius,
        )
        action_handler = SimulatedCoolDownAction(event_bus=event_bus)
        thermal_policy = ThermalPolicy(
            event_bus=event_bus,
            threshold=resolved_config.simulation.temp_threshold_celsius,
            action_handler=lambda request: action_handler.execute(
                request,
                approval_provider=(
                    hermes_approval_provider
                    if resolved_config.hermes.require_approval
                    else None
                ),
            ),
        )
        simulation_runtime = SimulationRuntime(
            scheduler=scheduler,
            sensor=sensor,
            thermal_policy=thermal_policy,
            action_handler=action_handler,
            interval_seconds=resolved_config.simulation.interval_seconds,
        )

    runtime = Runtime(event_bus, runtime_id=resolved_config.runtime.id)
    return SentinelApplication(
        config=resolved_config,
        event_bus=event_bus,
        runtime=runtime,
        audit_log=audit_log,
        scheduler=scheduler,
        hermes_notifier=hermes_notifier,
        hermes_approval_provider=hermes_approval_provider,
        simulation_runtime=simulation_runtime,
    )
