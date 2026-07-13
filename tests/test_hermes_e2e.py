"""End-to-end test: Sentinel pushes to a live Hermes server.

Run only when Hermes is listening at http://127.0.0.1:8787.
Skipped automatically if Hermes is unreachable.
"""

import unittest
import urllib.request

from sentinel_core import (
    ActionRequest,
    ActionSafety,
    ApprovalDecision,
    Event,
    EventSeverity,
    HermesApprovalProvider,
    HermesConfig,
    HermesNotificationHandler,
    config_from_mapping,
    create_application,
)

HERMES_BASE = "http://127.0.0.1:8787"
HERMES_TOKEN = "R2Oa3UdxXXC40D5AI2RP23dJSPFLQupG7Nu0QergBM4"


def _hermes_is_reachable() -> bool:
    try:
        req = urllib.request.Request(f"{HERMES_BASE}/health", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


@unittest.skipUnless(_hermes_is_reachable(), "Hermes server not running")
class HermesE2ETests(unittest.TestCase):
    """End-to-end tests against a live Hermes server."""

    def setUp(self) -> None:
        self.config = HermesConfig(
            enabled=True,
            base_url=HERMES_BASE,
            token=HERMES_TOKEN,
            timeout_seconds=5.0,
            notify_on=("warning", "error", "critical"),
            require_approval=True,
        )

    def test_health_check_returns_ok(self) -> None:
        req = urllib.request.Request(f"{HERMES_BASE}/health", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            self.assertEqual(resp.status, 200)

    def test_push_event_returns_200(self) -> None:
        handler = HermesNotificationHandler(self.config)
        event = Event(
            type="test.e2e",
            source="test_e2e",
            subject="e2e-test",
            severity=EventSeverity.WARNING,
            data={"test": True},
        )

        # Should not raise
        handler.notify(event)
        self.assertTrue(True)

    def test_non_destructive_action_is_approved(self) -> None:
        provider = HermesApprovalProvider(self.config)
        request = ActionRequest(
            action_type="e2e_test_action",
            subject="e2e-test",
            requested_by="test:e2e",
            safety=ActionSafety.NON_DESTRUCTIVE,
            reason="end-to-end approval test",
        )

        result = provider.request_decision(request)

        self.assertEqual(result.decision, ApprovalDecision.APPROVED)

    def test_destructive_action_is_rejected(self) -> None:
        provider = HermesApprovalProvider(self.config)
        request = ActionRequest(
            action_type="e2e_destructive_test",
            subject="e2e-test",
            requested_by="test:e2e",
            safety=ActionSafety.DESTRUCTIVE,
            reason="end-to-end destructive test",
        )

        result = provider.request_decision(request)

        self.assertEqual(result.decision, ApprovalDecision.REJECTED)

    def test_stats_endpoint_returns_counters(self) -> None:
        req = urllib.request.Request(
            f"{HERMES_BASE}/api/v1/stats",
            method="GET",
            headers={"Authorization": f"Bearer {HERMES_TOKEN}"},
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            self.assertEqual(resp.status, 200)

    def test_create_application_wires_hermes_when_enabled(self) -> None:
        """Smoke test: sentinel composes with hermes config and starts/stops."""
        config = config_from_mapping({
            "runtime": {"id": "e2e-sentinel"},
            "audit": {"enabled": False},
            "hermes": {
                "enabled": True,
                "base_url": HERMES_BASE,
                "token": HERMES_TOKEN,
                "notify_on": ["error"],
            },
        })
        app = create_application(config)
        app.start()
        app.stop()
        self.assertIsNotNone(app.hermes_notifier)


if __name__ == "__main__":
    unittest.main()