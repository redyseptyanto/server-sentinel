# Audit Specification

Audit records make Sentinel behavior inspectable after the fact. They are
append-only, machine-readable records derived from events.

## Requirements
- Every destructive action must have pre-action and post-action audit records.
- Runtime lifecycle events should be auditable.
- Audit writes should preserve event identifiers and timestamps.
- Audit records should be JSON-compatible.
- Audit sinks must never mutate prior records.

## Destructive Action Sequence
A destructive action must emit this minimum ordered event sequence:

1. `action.requested`
2. `action.approval_required`
3. `approval.decision_recorded`
4. `action.started`
5. `action.succeeded` or `action.failed`
6. `verification.started`
7. `verification.succeeded` or `verification.failed`

If approval is rejected, the sequence stops after `approval.decision_recorded`.
The decision event must include the rejection reason when available.

All events in the sequence share one `correlation_id`. Each event after
`action.requested` uses the previous event id as `causation_id`.

Required event data:
- action_id.
- action_type.
- safety.
- requested_by.
- approval decision when present.
- deterministic reason or error when available.
- verification details when available.

## Initial Sink
The initial reference runtime uses JSON Lines on local disk:
- One event per line.
- UTF-8 encoding.
- Parent directories are created if missing.
- Writes are flushed after each record.

## Future Sinks
Future audit sinks may include SQLite, remote append-only stores, or operating
system event logs. They must preserve the same event envelope semantics.
