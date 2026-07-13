# Product Requirements Document

## Problem
Host monitoring and recovery tooling is often fragmented, platform-specific, or
tightly coupled to one notification, metrics, or automation system. AI agents
also need a safe execution layer instead of direct privileged system access.

## Product
Sentinel is a cross-platform host monitoring and autonomous recovery runtime.
It observes host state, emits structured events, evaluates deterministic
policies, requests approval when required, executes approved actions, verifies
outcomes, and records audit history.

Sentinel core does not perform AI reasoning. External agents such as Hermes,
OpenAI Agents, Claude, or other orchestrators may reason over events and request
actions through explicit approval and action interfaces. Sentinel validates,
executes, verifies, and audits.

## Users
- Operators running Linux servers, homelab machines, or edge nodes.
- Developers building host automation plugins.
- AI-agent authors who need a bounded, auditable execution layer.
- Maintainers who need a small, understandable runtime that can be reviewed.

## Value Proposition
- One runtime for sensing, policy, approval, action, verification, audit, and
  notification.
- Plugin-first integration model so operators can choose their collectors,
  policy packs, approval providers, and notification sinks.
- Event-driven behavior where every state change is observable.
- Safety-first execution where destructive actions are approval-gated,
  validated, and auditable.

## Target Platforms
- Linux first.
- Windows and macOS after the core runtime and plugin contracts stabilize.

## Initial Features
- Runtime lifecycle management.
- In-process event bus for the reference runtime.
- Structured event envelope with correlation and causation identifiers.
- Append-only audit log.
- Plugin categories for sensors, policies, actions, verifiers, approval
  providers, and notification sinks.
- Linux sensors for CPU, memory, disk, NVMe, Docker, and system services.
- Thermal recovery policy pack.
- REST API.
- CLI.
- Telegram notifications as an optional plugin.
- Hermes approval provider as an optional plugin.

## Functional Requirements
- FR-001: Every state change MUST emit a structured event.
- FR-002: Every destructive action MUST be auditable before and after execution.
- FR-003: The core runtime MUST NOT host or invoke AI reasoning.
- FR-004: Policies MUST be deterministic and explainable from their inputs.
- FR-005: Action execution MUST be separated from approval decisions.
- FR-006: Failed verification MUST emit an event and preserve audit history.
- FR-007: Plugins MUST declare capabilities and required permissions.
- FR-008: Human override MUST win over autonomous behavior.

## Non-Functional Requirements
- NFR-001: The core should run with the least privileges required for enabled
  plugins.
- NFR-002: The event schema should remain stable across minor releases.
- NFR-003: The reference runtime should avoid mandatory external services.
- NFR-004: Configuration should be human-readable and versionable.
- NFR-005: The runtime should degrade safely when optional plugins fail.
- NFR-006: Audit records should be append-only and machine-readable.

## Success Metrics
- A new contributor can run tests and understand the runtime contract in less
  than 15 minutes.
- A sensor plugin can emit metrics without depending on policy or action code.
- A policy can request an action without knowing the approval provider.
- A destructive action leaves a complete audit trail.

## Non-Goals (v1)
- Full observability platform.
- SIEM replacement.
- Kubernetes operator.
- AI model hosting.
- Direct shell access for AI agents.
