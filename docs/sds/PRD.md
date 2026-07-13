# Product Requirements Document

## Problem
Host monitoring and recovery tooling is often fragmented, platform-specific, or
tightly coupled to one notification, metrics, or automation system. AI agents
also need a safe execution layer instead of direct privileged system access.

## Product
Sentinel is a cross-platform host monitoring and autonomous recovery runtime.
It observes host state, emits structured events, evaluates deterministic
policies, recommends safe recovery actions, requests approval when required,
executes approved actions, verifies outcomes, and records audit history.

Sentinel is the execution and observability layer for AI-managed systems. It is
not an AI assistant.

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
- Stable APIs that let Hermes and other agents manage hosts without direct
  privileged system access.

## Target Platforms
- Linux first.
- Windows and macOS after the core runtime and plugin contracts stabilize.

## Responsibilities
- Continuously observe the operating system and applications.
- Collect metrics, diagnostics, logs, and system state.
- Emit structured events.
- Evaluate configurable policies.
- Recommend safe recovery actions.
- Request approval from Hermes or another approval provider when required.
- Execute approved actions.
- Verify whether the action solved the problem.
- Record every workflow step in the audit log.

## Monitoring Scope
- Hardware monitoring: CPU temperature, utilization, frequency, memory, disk
  usage, SMART or NVMe health, network, battery where available, and GPU via
  optional plugins.
- Operating system monitoring: processes, services, system logs, boot status,
  and login sessions.
- Container monitoring: Docker Engine, Docker Compose projects, container
  health, logs, and resource usage.
- Application monitoring: user-defined health checks, HTTP endpoints, TCP
  services, and background workers.

## Event Engine
Everything produces events. Example event types include:
- `cpu.temperature.warning`
- `cpu.temperature.critical`
- `docker.container.unhealthy`
- `service.failed`
- `memory.high`
- `disk.almost_full`
- `network.offline`

## Policy Engine
Policies subscribe to events and never execute commands directly.
Policies emit recommendations and action requests.

Illustrative thermal recovery workflow:
1. CPU temperature remains above threshold.
2. Thermal policy emits an approval-gated action request.
3. Sentinel requests approval from the configured provider when required.
4. Sentinel executes the approved action.
5. Sentinel verifies whether the temperature returns to a safe range.
6. Sentinel escalates through the configured recovery ladder if the condition
   persists.

Every policy must be configurable.

## Safe Recovery Protocol
Every recovery action follows this sequence:
Observe -> Understand -> Recommend -> Approve -> Execute -> Verify -> Audit ->
Remember

Verification is mandatory.

## Approval Providers
Approval providers are interchangeable plugins.
Initial and planned examples:
- Hermes Telegram.
- CLI.
- Web UI.
- REST API.
- Future AI agents through stable provider contracts.

Hermes is one provider, not a special-case bypass.

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

Hermes communicates with Sentinel through stable APIs rather than direct system
access.

## Telegram Integration
Telegram-capable providers and notification plugins should support:
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

Approval should happen directly from Telegram where practical.

## Initial Features
- Runtime lifecycle management.
- In-process event bus for the reference runtime.
- Structured event envelope with correlation and causation identifiers.
- Append-only audit log.
- Plugin categories for sensors, policies, actions, verifiers, approval
  providers, query adapters, and notification sinks.
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
- FR-009: Policies MUST emit recommendations or action requests rather than
  direct command execution.
- FR-010: Hermes and other agents MUST integrate through stable APIs.
- FR-011: Approval providers MUST be interchangeable without changing policy
  logic.
- FR-012: Telegram notification and approval flows MUST remain optional plugins.

## Non-Functional Requirements
- NFR-001: The core should run with the least privileges required for enabled
  plugins.
- NFR-002: The event schema should remain stable across minor releases.
- NFR-003: The reference runtime should avoid mandatory external services.
- NFR-004: Configuration should be human-readable and versionable.
- NFR-005: The runtime should degrade safely when optional plugins fail.
- NFR-006: Audit records should be append-only and machine-readable.
- NFR-007: The core architecture should remain platform-agnostic while Linux is
  delivered first.
- NFR-008: The reference runtime should prefer minimal dependencies and clean
  interface boundaries.

## Success Metrics
- A new contributor can run tests and understand the runtime contract in less
  than 15 minutes.
- A sensor plugin can emit metrics without depending on policy or action code.
- A policy can request an action without knowing the approval provider.
- A destructive action leaves a complete audit trail.
- Hermes can operate through stable APIs without direct shell access.

## Non-Goals (v1)
- Full observability platform.
- SIEM replacement.
- Kubernetes operator.
- AI model hosting.
- Direct shell access for AI agents.
