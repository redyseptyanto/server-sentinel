"""Core integration ports.

These are AI-agnostic, stable contracts. Sentinel core never performs AI
reasoning; external agents such as Hermes consume these ports to receive
notifications and return approval decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sentinel_core.action_audit import ActionRequest, ApprovalDecision
from sentinel_core.events import Event


@dataclass(frozen=True, slots=True)
class ApprovalResult:
    """Decision returned by an approval provider, with supporting metadata."""

    decision: ApprovalDecision
    decided_by: str
    reason: str


class NotificationPort(Protocol):
    """Sends human-readable event summaries to an external channel."""

    def notify(self, event: Event) -> None:
        """Deliver an event summary to the notification channel."""


class ApprovalProviderPort(Protocol):
    """Accepts action requests and returns a decision with metadata."""

    def request_decision(self, request: ActionRequest) -> ApprovalResult:
        """Request an approval decision for the given action request."""