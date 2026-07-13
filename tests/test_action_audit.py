import unittest

from sentinel_core import (
    ActionAuditError,
    ActionAuditRecorder,
    ActionRequest,
    ActionSafety,
    ApprovalDecision,
    InMemoryEventBus,
)


class ActionAuditRecorderTests(unittest.TestCase):
    def test_destructive_action_sequence_preserves_correlation_and_causation(self) -> None:
        bus = InMemoryEventBus()
        request = ActionRequest(
            action_type="service.restart",
            subject="service:sshd",
            requested_by="policy:thermal-recovery",
            safety=ActionSafety.DESTRUCTIVE,
            reason="service is unhealthy after thermal recovery",
            parameters={"service": "sshd"},
        )
        recorder = ActionAuditRecorder(bus, request)

        recorder.record_requested()
        recorder.record_approval_required(reason="service restart can affect availability")
        recorder.record_approval_decision(
            ApprovalDecision.APPROVED,
            decided_by="human:operator",
            reason="approved during maintenance window",
        )
        recorder.record_started()
        recorder.record_succeeded(result={"exit_code": 0})
        recorder.record_verification_started()
        recorder.record_verification_succeeded(details={"service_active": True})

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
        self.assertTrue(
            all(event.correlation_id == request.correlation_id for event in bus.events)
        )
        self.assertIsNone(bus.events[0].causation_id)
        self.assertEqual(
            [event.causation_id for event in bus.events[1:]],
            [event.id for event in bus.events[:-1]],
        )
        self.assertEqual(bus.events[0].data["action_id"], request.id)
        self.assertEqual(bus.events[0].data["safety"], "destructive")

    def test_rejected_destructive_action_cannot_start(self) -> None:
        bus = InMemoryEventBus()
        request = ActionRequest(
            action_type="host.reboot",
            subject="host:edge-node-1",
            requested_by="provider:hermes",
            safety=ActionSafety.DESTRUCTIVE,
            reason="external agent requested reboot",
        )
        recorder = ActionAuditRecorder(bus, request)

        recorder.record_requested()
        recorder.record_approval_required(reason="host reboot affects availability")
        recorder.record_approval_decision(
            ApprovalDecision.REJECTED,
            decided_by="human:operator",
            reason="reboot rejected during business hours",
        )

        with self.assertRaises(ActionAuditError):
            recorder.record_started()

        self.assertEqual(
            [event.type for event in bus.events],
            [
                "action.requested",
                "action.approval_required",
                "approval.decision_recorded",
            ],
        )
        self.assertEqual(bus.events[-1].data["decision"], "rejected")

    def test_destructive_action_cannot_skip_approval_required(self) -> None:
        bus = InMemoryEventBus()
        request = ActionRequest(
            action_type="service.stop",
            subject="service:nginx",
            requested_by="policy:test",
            safety=ActionSafety.DESTRUCTIVE,
            reason="test",
        )
        recorder = ActionAuditRecorder(bus, request)

        recorder.record_requested()

        with self.assertRaises(ActionAuditError):
            recorder.record_approval_decision(
                ApprovalDecision.APPROVED,
                decided_by="human:operator",
                reason="approved",
            )

    def test_verification_cannot_start_before_action_result(self) -> None:
        bus = InMemoryEventBus()
        request = ActionRequest(
            action_type="diagnostic.collect",
            subject="host:edge-node-1",
            requested_by="operator",
            safety=ActionSafety.NON_DESTRUCTIVE,
            reason="operator requested diagnostics",
        )
        recorder = ActionAuditRecorder(bus, request)

        recorder.record_requested()
        recorder.record_started()

        with self.assertRaises(ActionAuditError):
            recorder.record_verification_started()


if __name__ == "__main__":
    unittest.main()
