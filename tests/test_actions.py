import unittest

from sentinel_core import (
    ActionRequest,
    ActionRouter,
    ActionSafety,
    ApprovalDecision,
    ApprovalResult,
    InMemoryEventBus,
    SimulatedCoolDownAction,
    SimulatedMitigationAction,
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
        self.assertEqual(logs, ["cooling down from 85.0C"])
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


class SimulatedMitigationActionTests(unittest.TestCase):
    def test_destructive_action_requires_approval_provider(self) -> None:
        bus = InMemoryEventBus()
        action = SimulatedMitigationAction(
            event_bus=bus,
            supported_action_types=("terminate_processes",),
            sleep_seconds=0.0,
        )
        request = ActionRequest(
            action_type="terminate_processes",
            subject="host.cpu",
            requested_by="policy:thermal",
            safety=ActionSafety.DESTRUCTIVE,
            reason="critical temperature",
            parameters={"termination_candidates": [{"pid": 123, "name": "python"}]},
        )

        result = action.execute(request)

        self.assertEqual(result.decision, ApprovalDecision.DEFERRED)
        self.assertEqual(
            [event.type for event in bus.events],
            [
                "action.requested",
                "action.approval_required",
                "approval.decision_recorded",
            ],
        )

    def test_destructive_action_runs_after_approval(self) -> None:
        bus = InMemoryEventBus()
        logs: list[str] = []
        action = SimulatedMitigationAction(
            event_bus=bus,
            supported_action_types=("reduce_workload",),
            sleep_seconds=0.0,
            logger=logs.append,
        )
        request = ActionRequest(
            action_type="reduce_workload",
            subject="host.cpu",
            requested_by="policy:thermal",
            safety=ActionSafety.DESTRUCTIVE,
            reason="emergency temperature",
            parameters={"top_cpu_processes": [{"pid": 123, "name": "python"}]},
        )

        result = action.execute(request, approval_provider=_ApproveAllProvider())

        self.assertEqual(result.decision, ApprovalDecision.APPROVED)
        self.assertEqual(logs, ["simulating graceful workload reduction"])
        self.assertEqual(
            [event.type for event in bus.events],
            [
                "action.requested",
                "action.approval_required",
                "approval.decision_recorded",
                "action.started",
                "action.succeeded",
                "verification.started",
                "verification.succeeded",
            ],
        )


class ActionRouterTests(unittest.TestCase):
    def test_router_dispatches_to_matching_handler(self) -> None:
        bus = InMemoryEventBus()
        router = ActionRouter(
            handlers=(
                SimulatedCoolDownAction(event_bus=bus, sleep_seconds=0.0),
                SimulatedMitigationAction(
                    event_bus=bus,
                    supported_action_types=("shutdown_host",),
                    sleep_seconds=0.0,
                ),
            )
        )
        request = ActionRequest(
            action_type="shutdown_host",
            subject="host.cpu",
            requested_by="policy:thermal",
            safety=ActionSafety.DESTRUCTIVE,
            reason="emergency temperature",
            parameters={},
        )

        result = router.execute(request, approval_provider=_ApproveAllProvider())

        self.assertEqual(result.decision, ApprovalDecision.APPROVED)
        self.assertIn("action.succeeded", [event.type for event in bus.events])


if __name__ == "__main__":
    unittest.main()
