# Architecture

## System Flow
Sensors -> Event Bus -> Policy Engine -> Approval Provider -> Action Engine ->
Verification -> Audit -> Notifications

The runtime owns lifecycle, event routing, configuration loading, and plugin
coordination. Everything else is attached through explicit ports.

## Core Boundary
Sentinel core MUST NOT perform AI reasoning. The core may expose facts,
validate requests, enforce deterministic policies, execute approved actions,
verify results, and emit events. Any natural-language reasoning, model calls,
planning, or agentic decision-making belongs outside the core boundary.

## Modules
- Runtime: owns lifecycle, state transitions, and module composition.
- Event Bus: publishes structured events to subscribers.
- Configuration Loader: validates human-readable configuration before startup.
- Scheduler: triggers sensors and recurring maintenance jobs.
- Policy Engine: evaluates deterministic policies from events and state.
- Approval Coordinator: asks approval providers for decisions.
- Action Engine: validates and executes approved actions.
- Verification Engine: checks post-action outcomes.
- Audit Sink: persists event and action history.
- Plugin Manager: loads plugin manifests and wires plugin capabilities.

## Ports
- SensorPort: collects host state and emits metric or diagnostic events.
- PolicyPort: converts events into action requests or suppressions.
- ApprovalProviderPort: accepts action requests and returns decisions.
- ActionPort: executes a bounded host operation.
- VerificationPort: verifies that an action achieved its requested outcome.
- NotificationPort: sends human-readable event summaries.
- AuditPort: records immutable event and action history.

## Plugin Model
Plugins are the extension boundary. The initial reference runtime supports
in-process plugins for development speed. The long-term contract should allow
out-of-process plugins for isolation and language independence.

Plugin categories:
- Sensors.
- Policies.
- Actions.
- Verifiers.
- Approval providers.
- Notifications.
- Diagnostic exporters.

Plugins must declare:
- Name and version.
- Category.
- Capabilities.
- Required permissions.
- Supported platforms.
- Configuration schema.

## Event Model
Events use a stable envelope:
- id: unique event identifier.
- type: namespaced event type.
- source: component or plugin that emitted the event.
- subject: host, plugin, policy, action, or resource the event is about.
- occurred_at: UTC timestamp.
- severity: debug, info, warning, error, or critical.
- correlation_id: workflow identifier shared by related events.
- causation_id: event identifier that directly caused this event.
- data: event-specific JSON-compatible payload.

Every state change emits an event. State changes include runtime lifecycle
changes, plugin lifecycle changes, policy decisions, approval decisions, action
status changes, verification results, audit write failures, and notification
delivery results.

## Safety Model
Actions are split into non-destructive and destructive classes.

Non-destructive actions read state or perform reversible operations.
Destructive actions may stop services, restart machines, delete data, alter
configuration, change network access, or otherwise affect availability or
integrity.

Destructive actions require:
- Explicit action definition.
- Permission declaration.
- Approval decision unless a policy grants pre-approved automation.
- Pre-action audit event.
- Post-action result event.
- Verification event.

## Data Flow Notes
The design borrows concepts, not code, from established OSS projects:
- Collector-style host sensing as seen in Prometheus node_exporter.
- Plugin categories and external extension boundaries as seen in Telegraf.
- State-transition alerting concepts as seen in Netdata.
- Scheduled host-state collection concepts as seen in osquery.

See `RESEARCH_NOTES.md` for source links.
