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

## Approval Providers
Approval providers are interchangeable plugins. Planned interfaces include:
- Hermes Telegram.
- CLI.
- Web UI.
- REST API.
- Future agent adapters.

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
remain an optional integration rather than a core dependency.

## Interface Rules
- Interfaces must be AI-agnostic.
- Interfaces must expose stable contracts across monitoring, approval, and
  manual action requests.
- Interfaces must not expose unrestricted shell access.
- Interfaces must preserve auditability and verification requirements.
