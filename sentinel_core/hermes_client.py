"""Hermes HTTP push client.

Implements NotificationPort and ApprovalProviderPort by pushing structured
events and action requests to an external Hermes REST endpoint.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from json import dumps, loads
from typing import Any
from urllib.error import URLError
from urllib.request import HTTPError, Request, urlopen

from sentinel_core.action_audit import (
    ActionRequest,
    ApprovalDecision,
)
from sentinel_core.config import HermesConfig
from sentinel_core.events import Event
from sentinel_core.ports import ApprovalResult


class HermesConnectionError(RuntimeError):
    """Raised when the Hermes endpoint is unreachable or returns an error."""


@dataclass(frozen=True, slots=True)
class HermesNotificationHandler:
    """NotificationPort implementation that pushes events to Hermes."""

    config: HermesConfig

    def notify(self, event: Event) -> None:
        """Push a single event to the Hermes endpoint."""
        _post_json(
            base_url=self.config.base_url,
            endpoint="/api/v1/events",
            token=self.config.token,
            timeout=self.config.timeout_seconds,
            payload=event.to_record(),
        )

    @staticmethod
    def event_filter(severities: tuple[str, ...]) -> Callable[[Event], bool]:
        """Return a filter that matches events whose severity is in *severities*."""

        def _filter(event: Event) -> bool:
            return event.severity.value in severities

        return _filter


@dataclass(frozen=True, slots=True)
class HermesApprovalProvider:
    """ApprovalProviderPort implementation that pushes to and polls Hermes."""

    config: HermesConfig

    def request_decision(self, request: ActionRequest) -> ApprovalResult:
        """Push an action request to Hermes and return the decision."""
        payload = {
            "action_id": request.id,
            "action_type": request.action_type,
            "subject": request.subject,
            "requested_by": request.requested_by,
            "safety": request.safety.value,
            "reason": request.reason,
            "parameters": dict(request.parameters),
            "correlation_id": request.correlation_id,
        }

        response = _post_json(
            base_url=self.config.base_url,
            endpoint="/api/v1/approval-requests",
            token=self.config.token,
            timeout=self.config.timeout_seconds,
            payload=payload,
        )

        raw_decision = response.get("decision", "deferred")
        decided_by = response.get("decided_by", "hermes")
        reason = response.get("reason", "")

        try:
            decision = ApprovalDecision(raw_decision)
        except ValueError:
            decision = ApprovalDecision.DEFERRED

        return ApprovalResult(
            decision=decision,
            decided_by=decided_by,
            reason=reason,
        )


def _post_json(
    base_url: str,
    endpoint: str,
    token: str,
    timeout: float,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """POST a JSON payload to a Hermes endpoint and return the parsed response."""
    url = f"{base_url.rstrip('/')}{endpoint}"
    body = dumps(payload).encode("utf-8")

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "User-Agent": "Sentinel/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        req = Request(url, data=body, headers=headers, method="POST")
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            if raw:
                return loads(raw.decode("utf-8"))
            return {}
    except HTTPError as exc:
        error_body = ""
        try:
            error_body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        raise HermesConnectionError(
            f"Hermes returned {exc.code} for {endpoint}: {error_body}"
        ) from exc
    except URLError as exc:
        raise HermesConnectionError(
            f"Hermes unreachable at {url}: {exc.reason}"
        ) from exc