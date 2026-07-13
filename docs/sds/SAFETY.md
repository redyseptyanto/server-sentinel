# Safety Specification

Sentinel is designed to execute bounded recovery actions without giving AI
agents direct system access.

## Rules
- Sentinel core MUST NOT perform AI reasoning.
- Human override always wins.
- Destructive actions require explicit permission and audit events.
- Action execution must be separate from approval.
- Verification must be separate from execution.
- Failed verification must emit an event.

## Destructive Actions
An action is destructive if it can affect availability, integrity, access,
configuration, or data. Examples include:
- Restarting or stopping services.
- Rebooting the host.
- Deleting files or volumes.
- Changing firewall or network configuration.
- Writing system configuration.

## Approval
Approval decisions may come from humans, configured deterministic automation, or
external approval providers. Approval providers may use AI outside Sentinel, but
Sentinel records only the decision and supporting metadata.

## Audit
Every destructive action must emit:
- action requested.
- approval required.
- approval decision.
- action started.
- action result.
- verification started.
- verification result.
