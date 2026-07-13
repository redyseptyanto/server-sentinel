# Domain Model

## Host
The machine observed or modified by Sentinel.

Fields:
- id: stable host identifier.
- hostname: current system hostname.
- platform: linux, windows, or macos.
- labels: operator-defined metadata.

## Sensor
A plugin or core component that observes host state and emits metric,
diagnostic, or lifecycle events. Sensors do not execute recovery actions.

## Metric
A point-in-time measurement emitted by a sensor.

Fields:
- name.
- value.
- unit.
- observed_at.
- tags.

## Event
An immutable fact emitted by the runtime or a plugin. Events are the primary
integration contract between subsystems.

Required fields:
- id.
- type.
- source.
- subject.
- occurred_at.
- severity.
- correlation_id.
- causation_id.
- data.

## Policy
A deterministic rule or ruleset that evaluates events and current state.
Policies may emit decisions, suppressions, or action requests. Policies must not
perform AI reasoning.

## Action
A bounded operation requested by a policy, approval provider, operator, or
external agent. Actions declare whether they are destructive.

Action lifecycle:
- requested.
- approval_required.
- approved.
- rejected.
- started.
- succeeded.
- failed.
- verification_started.
- verified.
- verification_failed.

## Approval
A decision that allows, rejects, or defers an action request. Approval may come
from a human, a configured automation policy, or an external approval provider.

## Provider
An integration that supplies approvals, notifications, diagnostics, or external
state. Providers are plugins and must declare permissions.

## Plugin
An extension package that implements one or more ports. Plugins are versioned,
configured, permissioned, and lifecycle-managed by the runtime.

## Notification
A human-readable message derived from an event or event group. Notifications are
delivery attempts, not the source of truth.

## Diagnostic
A structured explanation of runtime, plugin, policy, or action behavior.
Diagnostics must be derived from deterministic state and events.

## Audit Record
An immutable record of an event or action transition. Audit records are
append-only and machine-readable.
