# ADR 0002: Hermes HTTP Push Integration

Date: 2026-07-13

## Status
Accepted

## Context
Hermes is the AI reasoning agent that Sentinel serves. Per the architecture
boundary, Hermes must not have direct privileged system access; instead it
consumes live metrics, alerts, and action approvals through stable Sentinel
interfaces. The local environment already has a Hermes instance connected to
Telegram, but no bridge to Sentinel exists.

Multiple integration topologies were considered:
1. Sentinel exposes a pull API that Hermes polls.
2. Both sides maintain bidirectional connections.
3. Sentinel pushes events and approval requests to Hermes via HTTP.

## Decision
Sentinel pushes structured events and approval requests to Hermes over HTTP.

The push model was chosen because:
- It keeps Sentinel's output direction explicit and auditable — nothing
  external can call into Sentinel without authentication.
- Hermes is the single upstream consumer; event streaming to a push endpoint
  avoids the operational complexity of polling infrastructure at this stage.
- Approval can remain synchronous within the push call: Sentinel sends a
  request, Hermes returns a decision in the HTTP response, and Sentinel never
  blocks waiting for a separate poll cycle.

## Contract

### Event Push (`POST /api/v1/events`)
Sentinel POSTs the full `Event.to_record()` JSON body when the event severity
matches the configured `notify_on` list. Hermes should return `200` on accept.

### Approval Request (`POST /api/v1/approval-requests`)
Sentinel POSTs a JSON body with `action_id`, `action_type`, `subject`,
`requested_by`, `safety`, `reason`, `parameters`, and `correlation_id`.
Hermes must return a JSON body with `decision` (one of `approved`, `rejected`,
`deferred`), `decided_by`, and `reason`. Sentinel respects the returned
decision.

### Configuration
The `[hermes]` config table accepts:
- `enabled` (bool, default false)
- `base_url` (string, required when enabled)
- `token` (string, Bearer auth header)
- `timeout_seconds` (number, default 10.0)
- `notify_on` (list of severity strings, default ["warning", "error", "critical"])
- `require_approval` (bool, default true)

## Consequences
Positive:
- Hermes has a stable, documented push contract for events and approvals.
- The Hermes plugin is fully replaceable — `NotificationPort` and
  `ApprovalProviderPort` are core interfaces, and the HTTP client is one
  implementation.
- No new dependencies (stdlib-only `urllib`).
- Approval is synchronous in the HTTP round-trip, simplifying the flow.

Tradeoffs:
- If Hermes is unreachable, `HermesConnectionError` is raised and the caller
  (e.g. policy engine or action requestor) must handle the failure. No queuing
  or retry is built into the initial client.
- Synchronous approval blocks Sentinel's publisher until Hermes responds.
  Future iterations may move to an async approval callback pattern.

Follow-up:
- Add a durable event sink (AUDIT-003) so pushed events don't rely solely on
  Hermes uptime.
- Add retry/backoff in the Hermes client for transient failures.
- Consider async approval with a callback endpoint.