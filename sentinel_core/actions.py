"""Action implementations for the Sentinel reference runtime."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
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
            self.logger(f"cooling down from {temperature:.1f}°C")
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
