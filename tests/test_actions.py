import unittest

from sentinel_core import (
    ActionRequest,
    ActionSafety,
    ApprovalDecision,
    ApprovalProviderPort,
    ApprovalResult,
    InMemoryEventBus,
    SimulatedCoolDownAction,
)


class _ApproveAllProvider:
    def request_decision(self, request: ActionRequest) -> ApprovalResult:
        return ApprovalResult(
            decision=ApprovalDecision.APPROVED,
            decided_by="hermes",
            reason="approved for simulation",
        )


class _RejectProvider:
    def request_decision(self, request: ActionRequest) -> ApprovalResult:
        return ApprovalResult(
            decision=ApprovalDecision.REJECTED,
            decided_by="hermes",
            reason="rejected for simulation",
        )


class SimulatedCoolDownActionTests(unittest.TestCase):
    def test_execute_emits_success_and_verification_events(self) -> None:
        bus = InMemoryEventBus()
        logs: list[str] = []
        action = SimulatedCoolDownAction(
            event_bus=bus,
            sleep_seconds=0.0,
            logger=logs.append,
        )
        request = ActionRequest(
            action_type="cool_down",
            subject="host.cpu",
            requested_by="policy:thermal",
            safety=ActionSafety.NON_DESTRUCTIVE,
            reason="temperature too high",
            parameters={"temperature_celsius": 85.0},
        )

        result = action.execute(request)

        self.assertEqual(result.decision, ApprovalDecision.APPROVED)
        self.assertEqual(logs, ["cooling down from 85.0°C"])
        self.assertEqual(
            [event.type for event in bus.events],
            [
                "action.requested",
                "approval.decision_recorded",
                "action.started",
                "action.succeeded",
                "verification.started",
                "verification.succeeded",
            ],
        )

    def test_execute_uses_approval_provider_when_present(self) -> None:
        bus = InMemoryEventBus()
        action = SimulatedCoolDownAction(event_bus=bus, sleep_seconds=0.0)
        request = ActionRequest(
            action_type="cool_down",
            subject="host.cpu",
            requested_by="policy:thermal",
            safety=ActionSafety.NON_DESTRUCTIVE,
            reason="temperature too high",
            parameters={"temperature_celsius": 85.0},
        )

        result = action.execute(request, approval_provider=_ApproveAllProvider())

        self.assertEqual(result.decided_by, "hermes")
        self.assertEqual(bus.events[1].data["decision"], "approved")

    def test_rejected_action_stops_before_execution(self) -> None:
        bus = InMemoryEventBus()
        action = SimulatedCoolDownAction(event_bus=bus, sleep_seconds=0.0)
        request = ActionRequest(
            action_type="cool_down",
            subject="host.cpu",
            requested_by="policy:thermal",
            safety=ActionSafety.NON_DESTRUCTIVE,
            reason="temperature too high",
            parameters={"temperature_celsius": 85.0},
        )

        result = action.execute(request, approval_provider=_RejectProvider())

        self.assertEqual(result.decision, ApprovalDecision.REJECTED)
        self.assertEqual(
            [event.type for event in bus.events],
            ["action.requested", "approval.decision_recorded"],
        )


if __name__ == "__main__":
    unittest.main()
