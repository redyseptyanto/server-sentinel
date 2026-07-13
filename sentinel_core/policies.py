"""Policy implementations for the Sentinel reference runtime."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum

from sentinel_core.action_audit import ActionRequest, ActionSafety
from sentinel_core.config import ThermalPolicyConfig
from sentinel_core.events import Event, EventBus, EventSeverity


ActionRequestHandler = Callable[[ActionRequest], None]


class ThermalSeverity(IntEnum):
    NORMAL = 0
    WARNING = 1
    CRITICAL = 2
    EMERGENCY = 3


@dataclass(slots=True)
class ThermalPolicy:
    """Stateful thermal incident policy with warning/critical/emergency levels."""

    event_bus: EventBus
    config: ThermalPolicyConfig = field(default_factory=ThermalPolicyConfig)
    action_handler: ActionRequestHandler | None = None
    source: str = "sentinel.policy.thermal"
    _latest_by_subject: dict[str, dict[str, object]] = field(default_factory=dict, init=False)
    _cpu_warning_armed: bool = field(default=True, init=False)
    _cpu_critical_emitted: bool = field(default=False, init=False)
    _cpu_emergency_emitted: bool = field(default=False, init=False)
    _nvme_warning_armed: bool = field(default=True, init=False)
    _emergency_candidate_started_at: datetime | None = field(default=None, init=False)
    _emergency_mitigation_started_at: datetime | None = field(default=None, init=False)
    _emergency_shutdown_requested: bool = field(default=False, init=False)

    def subscribe(self) -> Callable[[], None]:
        """Subscribe the policy to metric events."""
        return self.event_bus.subscribe(
            self.handle_event,
            event_filter=lambda event: event.type == "sensor.metric_observed",
        )

    def handle_event(self, event: Event) -> Event | None:
        """Process a metric event and emit incident events and action requests."""
        self._latest_by_subject[event.subject] = dict(event.data)

        if event.subject == "host.cpu":
            return self._handle_cpu_event(event)
        if event.subject == "host.storage_health":
            return self._handle_storage_event(event)
        return None

    def _handle_cpu_event(self, event: Event) -> Event | None:
        temperature = self._numeric(event.data.get("temperature_celsius"))
        if temperature is None:
            return None

        severity = self._cpu_severity(temperature, event.occurred_at)

        emitted: Event | None = None
        if severity >= ThermalSeverity.WARNING and self._cpu_warning_armed:
            emitted = self._emit_incident_event(
                event=event,
                event_type="cpu.temperature.warning",
                severity=EventSeverity.WARNING,
                summary=self._incident_summary(temperature_celsius=temperature),
            )
            self._cpu_warning_armed = False

        if severity >= ThermalSeverity.CRITICAL and not self._cpu_critical_emitted:
            emitted = self._emit_incident_event(
                event=event,
                event_type="cpu.temperature.critical",
                severity=EventSeverity.ERROR,
                summary=self._incident_summary(temperature_celsius=temperature),
            )
            self._cpu_critical_emitted = True
            self._emit_action_request(
                event=event,
                action_type="terminate_processes",
                safety=ActionSafety.DESTRUCTIVE,
                reason=(
                    f"CPU temperature {temperature:.1f}C exceeded critical threshold "
                    f"{self.config.critical_cpu_threshold_celsius:.1f}C"
                ),
                parameters=self._critical_action_parameters(temperature),
            )

        if severity >= ThermalSeverity.EMERGENCY:
            if not self._cpu_emergency_emitted:
                emitted = self._emit_incident_event(
                    event=event,
                    event_type="cpu.temperature.emergency",
                    severity=EventSeverity.CRITICAL,
                    summary=self._incident_summary(temperature_celsius=temperature),
                )
                self._cpu_emergency_emitted = True
                self._emergency_mitigation_started_at = event.occurred_at
                self._emit_action_request(
                    event=event,
                    action_type="reduce_workload",
                    safety=ActionSafety.DESTRUCTIVE,
                    reason=(
                        f"CPU temperature {temperature:.1f}C remained at or above "
                        f"{self.config.emergency_cpu_threshold_celsius:.1f}C for "
                        f"{self.config.emergency_hold_seconds:.0f}s"
                    ),
                    parameters=self._emergency_action_parameters(
                        temperature,
                        escalation_step="reduce_workload",
                    ),
                )
            elif (
                not self._emergency_shutdown_requested
                and self._emergency_mitigation_started_at is not None
                and (
                    event.occurred_at - self._emergency_mitigation_started_at
                ).total_seconds()
                >= self.config.approval_timeout_seconds
            ):
                self._emergency_shutdown_requested = True
                self._emit_action_request(
                    event=event,
                    action_type="shutdown_host",
                    safety=ActionSafety.DESTRUCTIVE,
                    reason=(
                        f"CPU temperature remained at or above "
                        f"{self.config.emergency_cpu_threshold_celsius:.1f}C after "
                        f"{self.config.approval_timeout_seconds:.0f}s grace period"
                    ),
                    parameters=self._emergency_action_parameters(
                        temperature,
                        escalation_step="shutdown_host",
                    ),
                )

        if temperature < self.config.rearm_below_celsius:
            self._rearm_cpu(event, temperature)

        return emitted

    def _handle_storage_event(self, event: Event) -> Event | None:
        nvme_temperature = self._numeric(event.data.get("max_nvme_temperature_celsius"))
        if nvme_temperature is None:
            return None
        if (
            nvme_temperature >= self.config.warning_nvme_threshold_celsius
            and self._nvme_warning_armed
        ):
            emitted = self._emit_incident_event(
                event=event,
                event_type="nvme.temperature.warning",
                severity=EventSeverity.WARNING,
                summary=self._incident_summary(nvme_temperature_celsius=nvme_temperature),
            )
            self._nvme_warning_armed = False
            return emitted
        if nvme_temperature < self.config.rearm_below_celsius:
            self._nvme_warning_armed = True
        return None

    def _cpu_severity(self, temperature: float, observed_at: datetime) -> ThermalSeverity:
        if temperature >= self.config.emergency_cpu_threshold_celsius:
            if self._emergency_candidate_started_at is None:
                self._emergency_candidate_started_at = observed_at
                return ThermalSeverity.CRITICAL
            if (
                observed_at - self._emergency_candidate_started_at
            ).total_seconds() >= self.config.emergency_hold_seconds:
                return ThermalSeverity.EMERGENCY
            return ThermalSeverity.CRITICAL

        self._emergency_candidate_started_at = None
        if temperature >= self.config.critical_cpu_threshold_celsius:
            return ThermalSeverity.CRITICAL
        if temperature >= self.config.warning_cpu_threshold_celsius:
            return ThermalSeverity.WARNING
        return ThermalSeverity.NORMAL

    def _rearm_cpu(self, event: Event, temperature: float) -> None:
        was_incident = not self._cpu_warning_armed or self._cpu_critical_emitted or self._cpu_emergency_emitted
        self._cpu_warning_armed = True
        self._cpu_critical_emitted = False
        self._cpu_emergency_emitted = False
        self._emergency_candidate_started_at = None
        self._emergency_mitigation_started_at = None
        self._emergency_shutdown_requested = False
        if was_incident:
            self.event_bus.publish(
                Event(
                    type="cpu.temperature.recovered",
                    source=self.source,
                    subject=event.subject,
                    severity=EventSeverity.INFO,
                    correlation_id=event.correlation_id,
                    causation_id=event.id,
                    data=self._incident_summary(temperature_celsius=temperature),
                )
            )

    def _emit_incident_event(
        self,
        *,
        event: Event,
        event_type: str,
        severity: EventSeverity,
        summary: dict[str, object],
    ) -> Event:
        return self.event_bus.publish(
            Event(
                type=event_type,
                source=self.source,
                subject=event.subject,
                severity=severity,
                correlation_id=event.correlation_id,
                causation_id=event.id,
                data=summary,
            )
        )

    def _emit_action_request(
        self,
        *,
        event: Event,
        action_type: str,
        safety: ActionSafety,
        reason: str,
        parameters: dict[str, object],
    ) -> Event:
        request = ActionRequest(
            action_type=action_type,
            subject=event.subject,
            requested_by="policy:thermal",
            safety=safety,
            reason=reason,
            parameters=parameters,
            correlation_id=event.correlation_id,
        )
        emitted = self.event_bus.publish(
            Event(
                type="policy.action_requested",
                source=self.source,
                subject=event.subject,
                severity=EventSeverity.WARNING
                if safety is ActionSafety.NON_DESTRUCTIVE
                else EventSeverity.ERROR,
                correlation_id=event.correlation_id,
                causation_id=event.id,
                data={
                    "action_id": request.id,
                    "action_type": request.action_type,
                    "safety": request.safety.value,
                    "requested_by": request.requested_by,
                    "reason": request.reason,
                    "parameters": dict(request.parameters),
                },
            )
        )
        if self.action_handler is not None:
            self.action_handler(request)
        return emitted

    def _incident_summary(
        self,
        *,
        temperature_celsius: float | None = None,
        nvme_temperature_celsius: float | None = None,
    ) -> dict[str, object]:
        cpu = self._latest_by_subject.get("host.cpu", {})
        memory = self._latest_by_subject.get("host.memory", {})
        processes = self._latest_by_subject.get("host.processes", {})
        docker = self._latest_by_subject.get("host.docker", {})
        storage = self._latest_by_subject.get("host.storage_health", {})

        summary: dict[str, object] = {
            "approval_timeout_seconds": self.config.approval_timeout_seconds,
            "cpu_summary": cpu,
            "memory_summary": memory,
            "docker_summary": docker,
            "storage_summary": storage,
            "top_cpu_processes": processes.get("top_cpu_processes", []),
            "top_memory_processes": processes.get("top_memory_processes", []),
            "system_summary": {
                "process_count": processes.get("process_count"),
                "docker_running_count": docker.get("running_count"),
                "docker_unhealthy_count": docker.get("unhealthy_count"),
            },
        }
        if temperature_celsius is not None:
            summary["temperature_celsius"] = temperature_celsius
        if nvme_temperature_celsius is not None:
            summary["nvme_temperature_celsius"] = nvme_temperature_celsius
        return summary

    def _critical_action_parameters(self, temperature: float) -> dict[str, object]:
        top_cpu_processes = self._latest_by_subject.get("host.processes", {}).get(
            "top_cpu_processes",
            [],
        )
        candidates = [
            process
            for process in top_cpu_processes
            if isinstance(process, dict)
            and not self._is_protected_process(str(process.get("name", "")))
        ][: self.config.top_process_count]

        return {
            "temperature_celsius": temperature,
            "approval_timeout_seconds": self.config.approval_timeout_seconds,
            "protected_process_patterns": list(self.config.protected_process_patterns),
            "termination_candidates": candidates,
            "docker_summary": self._latest_by_subject.get("host.docker", {}),
        }

    def _emergency_action_parameters(
        self,
        temperature: float,
        *,
        escalation_step: str,
    ) -> dict[str, object]:
        return {
            "temperature_celsius": temperature,
            "approval_timeout_seconds": self.config.approval_timeout_seconds,
            "protected_process_patterns": list(self.config.protected_process_patterns),
            "escalation_step": escalation_step,
            "top_cpu_processes": self._latest_by_subject.get("host.processes", {}).get(
                "top_cpu_processes",
                [],
            ),
            "docker_summary": self._latest_by_subject.get("host.docker", {}),
            "system_summary": {
                "memory": self._latest_by_subject.get("host.memory", {}),
                "storage": self._latest_by_subject.get("host.storage_health", {}),
            },
        }

    def _is_protected_process(self, name: str) -> bool:
        lowered = name.lower()
        return any(pattern.lower() in lowered for pattern in self.config.protected_process_patterns)

    @staticmethod
    def _numeric(value: object) -> float | None:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return None
        return float(value)
