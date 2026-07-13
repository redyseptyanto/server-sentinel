"""Tests for the Hermes HTTP push client."""

from __future__ import annotations

import unittest
from json import dumps
from unittest.mock import MagicMock, patch

from sentinel_core import (
    ActionRequest,
    ActionSafety,
    ApprovalDecision,
    HermesApprovalProvider,
    HermesConnectionError,
    HermesConfig,
    HermesNotificationHandler,
)
from sentinel_core.events import Event, EventSeverity
from sentinel_core.ports import ApprovalResult


class _OkResponse:
    """Fake HTTP response for successful requests."""

    def __init__(self, body: bytes = b"") -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _OkResponse:
        return self

    def __exit__(self, *args: object) -> None:
        pass


def _fake_urlopen_ok(method: str, status: int, body: dict) -> MagicMock:
    """Return a mock urllib.request that succeeds with a JSON body."""
    mock = MagicMock()
    mock.return_value.__enter__.return_value.read.return_value = dumps(body).encode()
    mock.return_value.__enter__.return_value.status = status
    mock.return_value.__enter__.return_value.__enter__.return_value = (
        mock.return_value.__enter__.return_value
    )
    return mock


class HermesNotificationHandlerTests(unittest.TestCase):
    def test_notify_posts_to_event_endpoint(self) -> None:
        config = HermesConfig(
            enabled=True, base_url="http://hermes:8000", token="sekret"
        )
        handler = HermesNotificationHandler(config)
        event = Event(type="test.event", source="test", subject="runtime")

        with patch("sentinel_core.hermes_client.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value.read.return_value = b""
            handler.notify(event)

            call_args, call_kwargs = mock_urlopen.call_args
            req = call_args[0]
            self.assertIn("/api/v1/events", req.full_url)
            self.assertEqual(req.method, "POST")
            self.assertIn(b"test.event", req.data)
            self.assertEqual(req.headers["Authorization"], "Bearer sekret")

    def test_notify_connection_error_raises(self) -> None:
        config = HermesConfig(
            enabled=True, base_url="http://hermes:8000", token="sekret"
        )
        handler = HermesNotificationHandler(config)
        event = Event(type="test.event", source="test", subject="runtime")

        with patch(
            "sentinel_core.hermes_client.urlopen",
            side_effect=HermesConnectionError("unreachable"),
        ):
            with self.assertRaises(HermesConnectionError):
                handler.notify(event)

    def test_event_filter_matches_by_severity(self) -> None:
        filter_fn = HermesNotificationHandler.event_filter(
            ("warning", "error", "critical")
        )
        self.assertTrue(
            filter_fn(
                Event(
                    type="test", source="s", subject="s", severity=EventSeverity.ERROR
                )
            )
        )
        self.assertFalse(
            filter_fn(
                Event(
                    type="test", source="s", subject="s", severity=EventSeverity.INFO
                )
            )
        )


class HermesApprovalProviderTests(unittest.TestCase):
    def test_request_decision_posts_and_parses_approved(self) -> None:
        config = HermesConfig(
            enabled=True, base_url="http://hermes:8000", token="tok"
        )
        provider = HermesApprovalProvider(config)
        request = ActionRequest(
            action_type="restart_service",
            subject="nginx",
            requested_by="policy:thermal",
            safety=ActionSafety.DESTRUCTIVE,
            reason="cpu temp > 85C",
        )

        with patch("sentinel_core.hermes_client.urlopen") as mock_urlopen:
            response_body = {
                "decision": "approved",
                "decided_by": "hermes",
                "reason": "approved by operator",
            }
            mock_urlopen.return_value.__enter__.return_value.read.return_value = (
                dumps(response_body).encode()
            )

            result = provider.request_decision(request)

            self.assertIsInstance(result, ApprovalResult)
            self.assertEqual(result.decision, ApprovalDecision.APPROVED)
            self.assertEqual(result.decided_by, "hermes")
            self.assertEqual(result.reason, "approved by operator")

    def test_request_decision_defaults_to_deferred(self) -> None:
        config = HermesConfig(
            enabled=True, base_url="http://hermes:8000", token="tok"
        )
        provider = HermesApprovalProvider(config)
        request = ActionRequest(
            action_type="reboot",
            subject="host-01",
            requested_by="scheduler",
            safety=ActionSafety.DESTRUCTIVE,
            reason="scheduled maintenance",
        )

        with patch("sentinel_core.hermes_client.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value.read.return_value = b"{}"

            result = provider.request_decision(request)

            self.assertEqual(result.decision, ApprovalDecision.DEFERRED)
            self.assertEqual(result.decided_by, "hermes")

    def test_request_connection_error_raises(self) -> None:
        config = HermesConfig(
            enabled=True, base_url="http://hermes:8000", token="tok"
        )
        provider = HermesApprovalProvider(config)
        request = ActionRequest(
            action_type="restart_service",
            subject="nginx",
            requested_by="policy:thermal",
            safety=ActionSafety.NON_DESTRUCTIVE,
            reason="test",
        )

        with patch(
            "sentinel_core.hermes_client.urlopen",
            side_effect=HermesConnectionError("unreachable"),
        ):
            with self.assertRaises(HermesConnectionError):
                provider.request_decision(request)


if __name__ == "__main__":
    unittest.main()
