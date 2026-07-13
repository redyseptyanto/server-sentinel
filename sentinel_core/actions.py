"""Action implementations for the Sentinel reference runtime."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from time import sleep
from typing import Protocol

from sentinel_core.action_audit import (
    ActionAuditRecorder,
    ActionRequest,
    ApprovalDecision,
)
from sentinel_core.events import EventBus
from sentinel_core.ports import ApprovalProviderPort, ApprovalResult


class ActionPort(Protocol):
    """Stable execution contract for bounded host actions."""

    def can_handle(self, request: ActionRequest) -> bool:
        """Return whether this action implementation supports the request."""

    def execute(
        self,
        request: ActionRequest,
        *,
        approval_provider: ApprovalProviderPort | None = None,
    ) -> ApprovalResult:
        """Execute the action request and return the applied decision."""


@dataclass(slots=True)
class SimulatedCoolDownAction:
    """Simulated non-destructive thermal recovery action."""

    event_bus: EventBus
    sleep_seconds: float = 1.0
    logger: Callable[[str], None] | None = None
    source: str = "sentinel.action.simulated_cool_down"

    def can_handle(self, request: ActionRequest) -> bool:
        return request.action_type == "cool_down"

    def execute(
        self,
        request: ActionRequest,
        *,
        approval_provider: ApprovalProviderPort | None = None,
    ) -> ApprovalResult:
        if not self.can_handle(request):
            raise ValueError(f"unsupported action type: {request.action_type}")

        recorder = ActionAuditRecorder(self.event_bus, request, source=self.source)
        recorder.record_requested()

        decision = self._decision_for(request, approval_provider=approval_provider)
        recorder.record_approval_decision(
            decision.decision,
            decided_by=decision.decided_by,
            reason=decision.reason,
        )
        if decision.decision is not ApprovalDecision.APPROVED:
            return decision

        recorder.record_started()
        temperature = float(request.parameters.get("temperature_celsius", 0.0))
        if self.logger is not None:
            self.logger(f"cooling down from {temperature:.1f}C")
        sleep(self.sleep_seconds)
        simulated_temp = max(temperature - 15.0, 0.0)
        recorder.record_succeeded(
            result={
                "previous_temperature_celsius": temperature,
                "simulated_temperature_celsius": simulated_temp,
            }
        )
        recorder.record_verification_started()
        recorder.record_verification_succeeded(
            details={
                "simulated": True,
                "verified_temperature_celsius": simulated_temp,
            }
        )
        return decision

    def _decision_for(
        self,
        request: ActionRequest,
        *,
        approval_provider: ApprovalProviderPort | None,
    ) -> ApprovalResult:
        if approval_provider is not None:
            return approval_provider.request_decision(request)
        return ApprovalResult(
            decision=ApprovalDecision.APPROVED,
            decided_by="system",
            reason="non-destructive action auto-approved",
        )


@dataclass(slots=True)
class SimulatedMitigationAction:
    """Simulated destructive mitigation actions used by the thermal policy."""

    event_bus: EventBus
    supported_action_types: tuple[str, ...]
    sleep_seconds: float = 1.0
    logger: Callable[[str], None] | None = None
    source: str = "sentinel.action.simulated_mitigation"

    def can_handle(self, request: ActionRequest) -> bool:
        return request.action_type in self.supported_action_types

    def execute(
        self,
        request: ActionRequest,
        *,
        approval_provider: ApprovalProviderPort | None = None,
    ) -> ApprovalResult:
        if not self.can_handle(request):
            raise ValueError(f"unsupported action type: {request.action_type}")

        recorder = ActionAuditRecorder(self.event_bus, request, source=self.source)
        recorder.record_requested()
        recorder.record_approval_required(
            reason="destructive thermal mitigation requires approval"
        )

        decision = self._decision_for(request, approval_provider=approval_provider)
        recorder.record_approval_decision(
            decision.decision,
            decided_by=decision.decided_by,
            reason=decision.reason,
        )
        if decision.decision is not ApprovalDecision.APPROVED:
            return decision

        recorder.record_started()
        if self.logger is not None:
            self.logger(self._log_message_for(request))
        sleep(self.sleep_seconds)
        recorder.record_succeeded(
            result={
                "simulated": True,
                "action_type": request.action_type,
                "summary": self._summary_for(request),
            }
        )
        recorder.record_verification_started()
        recorder.record_verification_succeeded(
            details={
                "simulated": True,
                "action_type": request.action_type,
            }
        )
        return decision

    def _decision_for(
        self,
        request: ActionRequest,
        *,
        approval_provider: ApprovalProviderPort | None,
    ) -> ApprovalResult:
        if approval_provider is not None:
            return approval_provider.request_decision(request)
        return ApprovalResult(
            decision=ApprovalDecision.DEFERRED,
            decided_by="system",
            reason="destructive action requires an approval provider",
        )

    def _log_message_for(self, request: ActionRequest) -> str:
        if request.action_type == "terminate_processes":
            candidates = request.parameters.get("termination_candidates", [])
            return f"simulating graceful termination of {len(candidates) if isinstance(candidates, list) else 0} process candidates"
        if request.action_type == "reduce_workload":
            return "simulating graceful workload reduction"
        if request.action_type == "shutdown_host":
            return "simulating clean OS shutdown"
        return f"simulating action {request.action_type}"

    def _summary_for(self, request: ActionRequest) -> dict[str, object]:
        if request.action_type == "terminate_processes":
            return {
                "termination_candidates": request.parameters.get("termination_candidates", []),
                "protected_process_patterns": request.parameters.get(
                    "protected_process_patterns",
                    [],
                ),
            }
        if request.action_type == "reduce_workload":
            return {
                "docker_summary": request.parameters.get("docker_summary", {}),
                "top_cpu_processes": request.parameters.get("top_cpu_processes", []),
            }
        if request.action_type == "shutdown_host":
            return {
                "escalation_step": request.parameters.get("escalation_step", "shutdown_host"),
            }
        return {}


@dataclass(slots=True)
class ActionRouter:
    """Dispatch action requests to the first matching handler."""

    handlers: tuple[ActionPort, ...] = field(default_factory=tuple)

    def can_handle(self, request: ActionRequest) -> bool:
        return any(handler.can_handle(request) for handler in self.handlers)

    def execute(
        self,
        request: ActionRequest,
        *,
        approval_provider: ApprovalProviderPort | None = None,
    ) -> ApprovalResult:
        for handler in self.handlers:
            if handler.can_handle(request):
                return handler.execute(request, approval_provider=approval_provider)
        raise ValueError(f"unsupported action type: {request.action_type}")
