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
- Protected processes must not be targeted by automated termination unless
  explicitly allowed by configuration.

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

## Thermal Escalation Rules
- Warning incidents should notify once per incident and re-arm only after the
  host remains below the configured clear threshold.
- Critical incidents should prefer graceful termination of non-protected
  workload processes before stronger actions.
- Emergency incidents should not trigger immediate shutdown on the first hot
  sample. A configured hold period and verification steps are required.
- Emergency escalation should preserve a human approval opportunity through the
  configured provider before fallback automation is considered by a plugin or
  external approval service.
- SIGTERM-style graceful intent should be preferred before forceful
  termination, even in simulated workflows.
