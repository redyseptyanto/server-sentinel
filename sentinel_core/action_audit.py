"""Action audit event helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any
from uuid import uuid4

from sentinel_core.events import Event, EventBus, EventSeverity, JsonValue


class ActionAuditError(ValueError):
    """Raised when an action audit transition is invalid."""


class ActionSafety(StrEnum):
    """Safety classification for actions."""

    NON_DESTRUCTIVE = "non_destructive"
    DESTRUCTIVE = "destructive"


class ApprovalDecision(StrEnum):
    """Approval decision values."""

    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


@dataclass(frozen=True, slots=True)
class ActionRequest:
    """A bounded action request to be audited or executed later."""

    action_type: str
    subject: str
    requested_by: str
    safety: ActionSafety
    reason: str
    parameters: dict[str, JsonValue] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        _require_non_empty("action_type", self.action_type)
        _require_non_empty("subject", self.subject)
        _require_non_empty("requested_by", self.requested_by)
        _require_non_empty("reason", self.reason)
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))

    @property
    def is_destructive(self) -> bool:
        return self.safety == ActionSafety.DESTRUCTIVE


class ActionAuditRecorder:
    """Publish deterministic action audit events to an event bus."""

    def __init__(
        self,
        event_bus: EventBus,
        request: ActionRequest,
        *,
        source: str = "sentinel.action_audit",
    ) -> None:
        self._event_bus = event_bus
        self._request = request
        self._source = source
        self._last_event_id: str | None = None
        self._approval_decision: ApprovalDecision | None = None
        self._step = "initial"

    def record_requested(self) -> Event:
        self._require_step("initial", "action.requested")
        event = self._publish("action.requested", {"reason": self._request.reason})
        self._step = "requested"
        return event

    def record_approval_required(self, *, reason: str) -> Event:
        if not self._request.is_destructive:
            raise ActionAuditError("approval_required is only valid for destructive actions")
        self._require_step("requested", "action.approval_required")
        _require_non_empty("reason", reason)
        event = self._publish("action.approval_required", {"reason": reason})
        self._step = "approval_required"
        return event

    def record_approval_decision(
        self,
        decision: ApprovalDecision,
        *,
        decided_by: str,
        reason: str,
    ) -> Event:
        required_step = "approval_required" if self._request.is_destructive else "requested"
        self._require_step(required_step, "approval.decision_recorded")
        _require_non_empty("decided_by", decided_by)
        _require_non_empty("reason", reason)
        self._approval_decision = decision
        event = self._publish(
            "approval.decision_recorded",
            {
                "decision": decision.value,
                "decided_by": decided_by,
                "reason": reason,
            },
        )
        self._step = "approval_decided"
        return event

    def record_started(self) -> Event:
        if self._request.is_destructive:
            self._require_step("approval_decided", "action.started")
        elif self._step not in {"requested", "approval_decided"}:
            raise ActionAuditError("action.started cannot be recorded from current audit step")
        if self._request.is_destructive and self._approval_decision != ApprovalDecision.APPROVED:
            raise ActionAuditError("destructive actions must be approved before start")
        event = self._publish("action.started", {})
        self._step = "started"
        return event

    def record_succeeded(self, *, result: dict[str, JsonValue] | None = None) -> Event:
        self._require_step("started", "action.succeeded")
        event = self._publish("action.succeeded", {"result": result or {}})
        self._step = "completed"
        return event

    def record_failed(self, *, error: str) -> Event:
        self._require_step("started", "action.failed")
        _require_non_empty("error", error)
        event = self._publish("action.failed", {"error": error}, severity=EventSeverity.ERROR)
        self._step = "completed"
        return event

    def record_verification_started(self) -> Event:
        self._require_step("completed", "verification.started")
        event = self._publish("verification.started", {})
        self._step = "verification_started"
        return event

    def record_verification_succeeded(
        self,
        *,
        details: dict[str, JsonValue] | None = None,
    ) -> Event:
        self._require_step("verification_started", "verification.succeeded")
        event = self._publish("verification.succeeded", {"details": details or {}})
        self._step = "verified"
        return event

    def record_verification_failed(self, *, error: str) -> Event:
        self._require_step("verification_started", "verification.failed")
        _require_non_empty("error", error)
        event = self._publish(
            "verification.failed",
            {"error": error},
            severity=EventSeverity.ERROR,
        )
        self._step = "verified"
        return event

    def _publish(
        self,
        event_type: str,
        data: dict[str, JsonValue],
        *,
        severity: EventSeverity = EventSeverity.INFO,
    ) -> Event:
        event = self._event_bus.publish(
            Event(
                type=event_type,
                source=self._source,
                subject=self._request.subject,
                severity=severity,
                correlation_id=self._request.correlation_id,
                causation_id=self._last_event_id,
                data={
                    "action_id": self._request.id,
                    "action_type": self._request.action_type,
                    "safety": self._request.safety.value,
                    "requested_by": self._request.requested_by,
                    "parameters": dict(self._request.parameters),
                    **data,
                },
            )
        )
        self._last_event_id = event.id
        return event

    def _require_step(self, expected_step: str, event_type: str) -> None:
        if self._step != expected_step:
            raise ActionAuditError(
                f"{event_type} cannot be recorded from audit step {self._step}"
            )


def _require_non_empty(field_name: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ActionAuditError(f"{field_name} must be a non-empty string")
