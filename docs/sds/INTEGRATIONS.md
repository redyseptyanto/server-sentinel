# Integrations Specification

Sentinel exposes trusted execution and observability through stable interfaces.
External agents reason. Sentinel validates, executes, verifies, and audits.

## Hermes Integration
Hermes must be able to:
- Read live metrics.
- Read diagnostics.
- Read logs.
- Query Docker state.
- Query services.
- Receive alerts.
- Approve actions.
- Reject actions.
- Trigger actions manually.
- Request reports.

Hermes interacts with Sentinel through stable APIs and approval provider
contracts rather than direct system access.

### Push Contract (Current)
Sentinel pushes events and approval requests to Hermes over HTTP. The contract
is documented in `docs/adr/0002-hermes-http-push-integration.md`.

#### Event Push
- Endpoint: `POST {base_url}/api/v1/events`
- Auth: `Authorization: Bearer {token}`
- Body: `Event.to_record()` (full JSON envelope)
- Response: `200` on accept (body ignored)

Sentinel only pushes events whose severity matches the configured `notify_on`
list.

#### Approval Request
- Endpoint: `POST {base_url}/api/v1/approval-requests`
- Auth: `Authorization: Bearer {token}`
- Body:
  ```json
  {
    "action_id": "uuid",
    "action_type": "restart_service",
    "subject": "nginx",
    "requested_by": "policy:thermal",
    "safety": "destructive",
    "reason": "cpu temp > 85C",
    "parameters": {},
    "correlation_id": "uuid"
  }
  ```
- Response body:
  ```json
  {
    "decision": "approved",
    "decided_by": "hermes",
    "reason": "approved by operator"
  }
  ```
  `decision` must be one of `approved`, `rejected`, `deferred`. Sentinel
  respects the returned decision and emits the appropriate audit event.

### Future API (Planned)
When Sentinel gains a REST API (Phase 9), Hermes will also be able to pull
live metrics, logs, and Docker state directly, while the push contract
continues to cover alerts and approval.

## Approval Providers
Approval providers are interchangeable plugins. Planned interfaces include:
- Hermes Telegram.
- CLI.
- Web UI.
- REST API.
- Future agent adapters.
- **Hermes HTTP push** (current implementation).

Approval providers return decisions and supporting metadata. They do not bypass
Sentinel safety policy.

## Telegram Integration
Telegram-capable plugins should support:
- Warning events.
- Critical events.
- Recovery recommendations.
- Approval requests.
- Recovery progress.
- Recovery results.
- System startup.
- System shutdown.
- Daily health summaries.
- Weekly reports.

Approval should happen directly from Telegram where practical, but Telegram must
remain an optional integration rather than a core dependency. The Hermes push
contract allows Telegram notifications to be handled by Hermes itself, which
already has a Telegram channel configured.

## Interface Rules
- Interfaces must be AI-agnostic.
- Interfaces must expose stable contracts across monitoring, approval, and
  manual action requests.
- Interfaces must not expose unrestricted shell access.
- Interfaces must preserve auditability and verification requirements.

## Current Implementation
- `sentinel_core/ports.py`: `NotificationPort` and `ApprovalProviderPort`
  abstract contracts.
- `sentinel_core/hermes_client.py`: `HermesNotificationHandler` and
  `HermesApprovalProvider` — stdlib-only HTTP push implementations.
- `sentinel_core/config.py`: `HermesConfig` dataclass with validation.
- `sentinel_core/__init__.py`: exported symbols.
- `sentinel_core/application.py`: composition root wires Hermes notifier and
  approval provider when `hermes.enabled = true`.
- `docs/adr/0002-hermes-http-push-integration.md`: architecture decision record.
